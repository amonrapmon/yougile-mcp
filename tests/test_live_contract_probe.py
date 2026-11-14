"""Offline safety and orchestration tests for the live contract probe."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import live_contract_probe as probe
from yougile_mcp.api.errors import SchemaDiagnostic, UncertainWriteError, UpstreamError
from yougile_mcp.api.spec import operations
from yougile_mcp.config import Settings


PREFIX = "YOUGILE_MCP_E2E_GEN229_TEST01"


class LiveContractProbeTests(unittest.IsolatedAsyncioTestCase):
    def test_plan_preview_marks_every_operation_without_live_evidence(self):
        plan = probe.build_read_only_plan()
        report = probe.build_plan_preview(plan, request_limit=20)
        planned_ids = {step["operationId"] for step in plan["steps"]}

        self.assertEqual(len(report["operations"]), 72)
        self.assertEqual(report["requests_used"], 0)
        self.assertEqual(
            {row["operationId"] for row in report["operations"] if row["planned"]},
            planned_ids,
        )
        self.assertTrue(all(row["status"] != "PASS" for row in report["operations"]))

    def test_sensitive_participants_must_be_approved_and_in_fixture_allowlist(self):
        common = {
            "fixture_ids": {"test-task", "test-user"},
            "created_ids": set(),
            "observed_ids": set(),
            "fixture_prefix": PREFIX,
            "callback_urls": set(),
            "allow_writes": True,
            "allow_destructive": False,
        }
        arguments = {
            "operation": operations()["TaskController_updateChatSubscribers"],
            "path": {"id": "test-task"},
            "body": {"content": ["real-user"]},
            "multipart_file": None,
        }

        self.assertEqual(
            probe._fixture_gate(**arguments, **common, allow_sensitive=False),
            "sensitive_operation_approval_required",
        )
        self.assertEqual(
            probe._fixture_gate(**arguments, **common, allow_sensitive=True),
            "subscriber_not_in_fixture_allowlist",
        )
        self.assertIsNone(
            probe._fixture_gate(
                **{**arguments, "body": {"content": ["test-user"]}},
                **common,
                allow_sensitive=True,
            )
        )

    def test_group_chat_members_must_be_in_fixture_allowlist(self):
        common = {
            "operation": operations()["GroupChatController_update"],
            "path": {"id": "test-chat"},
            "multipart_file": None,
            "fixture_ids": {"test-chat", "test-user"},
            "created_ids": set(),
            "observed_ids": set(),
            "fixture_prefix": PREFIX,
            "callback_urls": set(),
            "allow_writes": True,
            "allow_destructive": False,
            "allow_sensitive": True,
        }

        self.assertEqual(
            probe._fixture_gate(
                **common,
                body={"users": {"real-user": {"notified": True}}},
            ),
            "chat_member_not_in_fixture_allowlist",
        )
        self.assertIsNone(
            probe._fixture_gate(
                **common,
                body={"users": {"test-user": {"notified": True}}},
            )
        )

    def test_default_matrix_covers_all_operations_and_read_plan_is_write_free(self):
        matrix = probe.build_report()
        operation_ids = {row["operationId"] for row in matrix["operations"]}
        self.assertEqual(len(operation_ids), 72)
        self.assertEqual(operation_ids, set(operations()))

        plan = probe.build_read_only_plan()
        plan_ids = {step["operationId"] for step in plan["steps"]}
        expected_ids = {
            operation_id
            for operation_id, operation in operations().items()
            if operation.effect == "read"
            and operation_id not in probe._CREDENTIAL_OPERATIONS
            and operation_id != "CrmExternalIdController_findContactByExternalId"
            and operation_id not in probe.PREFLIGHT_OPERATION_IDS
        }
        self.assertEqual(plan_ids, expected_ids)
        self.assertTrue(all(operations()[item].effect == "read" for item in plan_ids))

    def test_profile_env_loader_reads_only_expected_names(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "e2e.env"
            path.write_text(
                "YOUGILE_API_KEY=synthetic-key\nYOUGILE_COMPANY_ID=synthetic-company\nOTHER=value\n",
                encoding="utf-8",
            )
            with patch.dict(os.environ, {}, clear=True):
                self.assertTrue(probe.load_local_credentials(path))
                self.assertEqual(os.environ["YOUGILE_API_KEY"], "synthetic-key")
                self.assertEqual(os.environ["YOUGILE_COMPANY_ID"], "synthetic-company")
                self.assertNotIn("OTHER", os.environ)

    def test_manifest_rejects_credentials_without_echoing_them(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(
                json.dumps(
                    {
                        "company_scope": "disposable_test_company",
                        "fixture_ids": [],
                        "fixture_prefix": PREFIX,
                        "steps": [],
                        "apiKey": "PRIVATE_VALUE",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.PlanError) as raised:
                probe.load_plan(path)
        self.assertNotIn("PRIVATE_VALUE", str(raised.exception))

    async def test_full_safe_pass_continues_after_schema_failure(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": [],
            "fixture_prefix": PREFIX,
            "steps": [
                {"step_id": "projects", "operationId": "ProjectController_search", "query": {"limit": 1}},
                {"step_id": "boards", "operationId": "BoardController_search", "query": {"limit": 1}},
            ],
        }
        calls = []

        class FakeClient:
            def __init__(self, _settings, *, timeout, max_requests):
                self.requests_sent = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def request(self, operation_id, **_kwargs):
                calls.append(operation_id)
                self.requests_sent += 1
                if operation_id == "ProjectController_search":
                    raise UpstreamError(
                        status_code=200,
                        diagnostic=SchemaDiagnostic(
                            path="content.[item].deleted",
                            rule="type",
                            expected_type="boolean",
                            actual_type="null",
                        ),
                    )
                data = {"paging": {"limit": 1, "offset": 0, "next": False}, "content": []}
                if operation_id == "CompanyController_get":
                    data = {"id": "test-company"}
                return SimpleNamespace(status_code=200, data=data)

        settings = Settings.from_env(
            {"YOUGILE_API_KEY": "synthetic-key", "YOUGILE_COMPANY_ID": "test-company"}
        )
        with (
            patch.object(probe, "YouGileClient", FakeClient),
            patch.object(probe, "load_local_credentials", return_value=True),
            patch.object(Settings, "from_env", return_value=settings),
        ):
            report = await probe.execute_plan(
                plan,
                request_limit=10,
                confirm_disposable_company=True,
                allow_writes=False,
                allow_destructive=False,
                allow_sensitive=False,
            )

        self.assertEqual(calls, [*probe.PREFLIGHT_OPERATION_IDS, "ProjectController_search", "BoardController_search"])
        self.assertEqual(probe._find_row(report, "ProjectController_search")["status"], "FAIL")
        self.assertEqual(probe._find_row(report, "ProjectController_search")["schema"]["actual_type"], "null")
        self.assertEqual(probe._find_row(report, "BoardController_search")["status"], "PASS")
        self.assertEqual(report["requests_used"], 4)

    async def test_empty_collection_skips_dependent_detail_and_continues(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": [],
            "fixture_prefix": PREFIX,
            "steps": [
                {"step_id": "projects", "operationId": "ProjectController_search", "query": {"limit": 1}},
                {"step_id": "project", "operationId": "ProjectController_get", "path": {"id": "$projects.content.0.id"}},
                {"step_id": "boards", "operationId": "BoardController_search", "query": {"limit": 1}},
            ],
        }
        calls = []

        class FakeClient:
            def __init__(self, _settings, *, timeout, max_requests):
                self.requests_sent = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def request(self, operation_id, **_kwargs):
                calls.append(operation_id)
                self.requests_sent += 1
                if operation_id == "CompanyController_get":
                    return SimpleNamespace(status_code=200, data={"id": "test-company"})
                data = {"paging": {"limit": 1, "offset": 0, "next": False}, "content": []}
                return SimpleNamespace(status_code=200, data=data)

        settings = Settings.from_env(
            {"YOUGILE_API_KEY": "synthetic-key", "YOUGILE_COMPANY_ID": "test-company"}
        )
        with (
            patch.object(probe, "YouGileClient", FakeClient),
            patch.object(probe, "load_local_credentials", return_value=True),
            patch.object(Settings, "from_env", return_value=settings),
        ):
            report = await probe.execute_plan(
                plan,
                request_limit=10,
                confirm_disposable_company=True,
                allow_writes=False,
                allow_destructive=False,
                allow_sensitive=False,
            )

        self.assertEqual(calls, [*probe.PREFLIGHT_OPERATION_IDS, "ProjectController_search", "BoardController_search"])
        self.assertEqual(probe._find_row(report, "ProjectController_search")["status"], "PASS")
        self.assertEqual(probe._find_row(report, "ProjectController_get")["status"], "SKIPPED")
        self.assertEqual(probe._find_row(report, "ProjectController_get")["category"], "no_test_fixture_found")
        self.assertEqual(probe._find_row(report, "BoardController_search")["status"], "PASS")

    async def test_uncertain_write_stops_remaining_plan_steps(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": ["test-column"],
            "fixture_prefix": PREFIX,
            "steps": [
                {
                    "step_id": "task_create",
                    "operationId": "TaskController_create",
                    "body": {"title": PREFIX, "columnId": "test-column"},
                },
                {
                    "step_id": "board_create",
                    "operationId": "BoardController_create",
                    "body": {"title": PREFIX, "projectId": "test-project"},
                },
            ],
        }
        calls = []

        class FakeClient:
            def __init__(self, _settings, *, timeout, max_requests):
                self.requests_sent = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def request(self, operation_id, **_kwargs):
                calls.append(operation_id)
                self.requests_sent += 1
                if operation_id == "CompanyController_get":
                    return SimpleNamespace(status_code=200, data={"id": "test-company"})
                if operation_id == "TaskController_create":
                    raise UncertainWriteError()
                return SimpleNamespace(status_code=200, data={"id": "safe-id"})

        settings = Settings.from_env(
            {"YOUGILE_API_KEY": "synthetic-key", "YOUGILE_COMPANY_ID": "test-company"}
        )
        with (
            patch.object(probe, "YouGileClient", FakeClient),
            patch.object(probe, "load_local_credentials", return_value=True),
            patch.object(Settings, "from_env", return_value=settings),
        ):
            report = await probe.execute_plan(
                plan,
                request_limit=10,
                confirm_disposable_company=True,
                allow_writes=True,
                allow_destructive=False,
                allow_sensitive=False,
            )

        self.assertEqual(calls, [*probe.PREFLIGHT_OPERATION_IDS, "TaskController_create"])
        self.assertEqual(probe._find_row(report, "TaskController_create")["category"], "uncertain_write")
        self.assertEqual(probe._find_row(report, "BoardController_create")["category"], "stopped_after_uncertain_write")


if __name__ == "__main__":
    unittest.main()
