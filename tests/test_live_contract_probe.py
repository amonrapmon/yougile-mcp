"""Offline safety and orchestration tests for the live contract probe."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from scripts import live_contract_probe as probe
from yougile_mcp.api.errors import NotFoundError, SchemaDiagnostic, UncertainWriteError, UpstreamError
from yougile_mcp.api.spec import operations
from yougile_mcp.config import Settings


PREFIX = "YOUGILE_MCP_E2E_GEN229_TEST01"


class LiveContractProbeTests(unittest.IsolatedAsyncioTestCase):
    def test_resolve_replaces_reference_keys_in_nested_objects(self):
        self.assertEqual(
            probe._resolve(
                {
                    "users": {"$user.id": {"notified": False}},
                    "userRoleMap": {"$user.id": "user"},
                },
                {"user": {"id": "test-user"}},
            ),
            {
                "users": {"test-user": {"notified": False}},
                "userRoleMap": {"test-user": "user"},
            },
        )

    def test_report_shows_webhook_state_check_without_entity_data(self):
        report = probe.build_report()
        report["side_effect_checks"]["webhook_state"] = {
            "status": "PASS",
            "category": "webhook_state_observed",
            "observations": [
                {"status": "PASS", "category": "webhook_state_observed"},
                {"status": "PASS", "category": "webhook_state_observed"},
            ],
        }
        output = StringIO()
        with redirect_stdout(output):
            probe._print_report(report)
        self.assertIn("webhook state signal: PASS webhook_state_observed observations=2", output.getvalue())
        self.assertNotIn("webhook_id", output.getvalue())

    def test_side_effect_summary_retains_failure_across_later_success(self):
        report = probe.build_report()
        probe._record_side_effect_check(report, "webhook_state", "FAIL", "webhook_state_mismatch")
        probe._record_side_effect_check(report, "webhook_state", "PASS", "webhook_state_observed")
        self.assertEqual(report["side_effect_checks"]["webhook_state"]["status"], "FAIL")
        self.assertEqual(len(report["side_effect_checks"]["webhook_state"]["observations"]), 2)

    def test_plan_preview_marks_every_operation_without_live_evidence(self):
        plan = probe.build_read_only_plan()
        report = probe.build_plan_preview(plan, request_limit=20)
        planned_ids = {step["operationId"] for step in plan["steps"]}

        self.assertEqual(len(report["operations"]), 72)
        self.assertEqual(report["requests_used"], 0)
        self.assertEqual(
            {row["operationId"] for row in report["operations"] if row["planned"]},
            planned_ids | set(probe.PREFLIGHT_OPERATION_IDS),
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

    def test_callback_delivery_requires_owner_confirmation_and_test_only_filters(self):
        common = {
            "operation": operations()["WebhookController_create"],
            "path": {},
            "multipart_file": None,
            "fixture_ids": {"test-project"},
            "created_ids": set(),
            "observed_ids": set(),
            "fixture_prefix": PREFIX,
            "callback_urls": {"https://n8n.example.invalid/webhook/test"},
            "allow_writes": True,
            "allow_destructive": False,
            "allow_sensitive": True,
        }
        body = {
            "url": "https://n8n.example.invalid/webhook/test",
            "event": "task-*",
            "filters": [
                {"name": "location", "value": ["test-project"]},
                {"name": "title", "value": [f"^{PREFIX}"]},
            ],
        }

        self.assertEqual(
            probe._fixture_gate(**common, body=body),
            "callback_workflow_not_verified",
        )
        self.assertIsNone(
            probe._fixture_gate(**common, body=body, confirm_callback_workflow_safe=True)
        )

    def test_global_custom_status_operations_exceed_disposable_company_scope(self):
        for operation_id in probe._CROSS_COMPANY_SCOPE_OPERATIONS:
            with self.subTest(operation=operation_id):
                self.assertEqual(
                    probe._fixture_gate(
                        operations()[operation_id],
                        path={},
                        body={"text": PREFIX, "emoji": "🧪"},
                        multipart_file=None,
                        fixture_ids=set(),
                        created_ids=set(),
                        observed_ids=set(),
                        fixture_prefix=PREFIX,
                        callback_urls=set(),
                        allow_writes=True,
                        allow_destructive=True,
                        allow_sensitive=True,
                        confirm_callback_workflow_safe=True,
                    ),
                    "operation_scope_exceeds_disposable_company",
                )

    def test_webhook_delivery_signal_uses_server_success_metadata(self):
        self.assertEqual(
            probe._webhook_delivery_signal(
                [{"id": "test-hook", "lastSuccess": 123, "failuresSinceLastSuccess": 0}],
                "test-hook",
            ),
            ("PASS", "server_last_success_observed"),
        )
        self.assertEqual(
            probe._webhook_delivery_signal(
                [{"id": "test-hook", "failuresSinceLastSuccess": 1}], "test-hook"
            ),
            ("FAIL", "delivery_failures_reported"),
        )
        self.assertEqual(
            probe._webhook_delivery_signal([{"id": "test-hook"}], "test-hook"),
            ("PENDING", "no_server_success_signal"),
        )

    def test_webhook_state_signal_verifies_disable_and_delete(self):
        record = {"id": "test-hook", "disabled": True, "deleted": True}
        self.assertEqual(
            probe._webhook_state_signal(
                [record], "test-hook", {"webhook_id": "$hook.id", "disabled": True}
            ),
            ("PASS", "webhook_state_observed"),
        )
        self.assertEqual(
            probe._webhook_state_signal(
                [record], "test-hook", {"webhook_id": "$hook.id", "deleted": False}
            ),
            ("FAIL", "webhook_state_mismatch"),
        )

    def test_plan_loader_allows_repeated_operations_with_distinct_steps(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(
                json.dumps(
                    {
                        "company_scope": "disposable_test_company",
                        "fixture_ids": [],
                        "fixture_prefix": PREFIX,
                        "steps": [
                            {"step_id": "search_before", "operationId": "ProjectController_search"},
                            {"step_id": "search_after", "operationId": "ProjectController_search"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            plan = probe.load_plan(path)
        self.assertEqual(len(plan["steps"]), 2)

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
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(status_code=200, data=[])
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
        self.assertEqual(report["requests_used"], 5)

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
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(status_code=200, data=[])
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

    async def test_repeated_operation_steps_aggregate_failures_and_count_attempts(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": [],
            "fixture_prefix": PREFIX,
            "steps": [
                {"step_id": "search_first", "operationId": "ProjectController_search", "query": {"limit": 1}},
                {"step_id": "search_second", "operationId": "ProjectController_search", "query": {"limit": 1}},
            ],
        }
        calls = []
        search_calls = 0

        class FakeClient:
            def __init__(self, _settings, *, timeout, max_requests):
                self.requests_sent = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def request(self, operation_id, **_kwargs):
                nonlocal search_calls
                calls.append(operation_id)
                self.requests_sent += 1
                if operation_id == "CompanyController_get":
                    return SimpleNamespace(status_code=200, data={"id": "test-company"})
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(status_code=200, data=[])
                if operation_id == "ProjectController_search":
                    search_calls += 1
                    if search_calls == 1:
                        raise UpstreamError(status_code=200)
                    return SimpleNamespace(
                        status_code=200,
                        data={"paging": {"limit": 1, "offset": 0, "next": False}, "content": []},
                    )
                return SimpleNamespace(status_code=200, data={})

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

        row = probe._find_row(report, "ProjectController_search")
        self.assertEqual(calls, [*probe.PREFLIGHT_OPERATION_IDS, "ProjectController_search", "ProjectController_search"])
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["invocations"], 2)
        self.assertEqual(row["http_attempts"], 2)
        self.assertEqual([item["status"] for item in row["step_results"]], ["FAIL", "PASS"])
        self.assertEqual(report["requests_used"], 5)

    async def test_created_numeric_message_id_allows_its_detail_read(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": ["test-chat"],
            "fixture_prefix": PREFIX,
            "steps": [
                {
                    "step_id": "message",
                    "operationId": "ChatMessageController_sendMessage",
                    "path": {"chatId": "test-chat"},
                    "body": {"text": PREFIX, "textHtml": PREFIX, "label": PREFIX},
                },
                {
                    "step_id": "message_detail",
                    "operationId": "ChatMessageController_get",
                    "path": {"chatId": "test-chat", "id": "$message.id"},
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
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(status_code=200, data=[])
                if operation_id == "ChatMessageController_sendMessage":
                    return SimpleNamespace(status_code=201, data={"id": 12345})
                return SimpleNamespace(status_code=200, data={"id": 12345})

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
                allow_sensitive=True,
            )

        self.assertEqual(
            calls,
            [*probe.PREFLIGHT_OPERATION_IDS, "ChatMessageController_sendMessage", "ChatMessageController_get"],
        )
        self.assertEqual(probe._find_row(report, "ChatMessageController_get")["status"], "PASS")

    async def test_plan_can_assert_expected_synthetic_not_found(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": [],
            "fixture_prefix": PREFIX,
            "steps": [
                {
                    "step_id": "external_lookup",
                    "operationId": "CrmExternalIdController_findContactByExternalId",
                    "query": {"provider": "gen229-e2e", "chatId": f"{PREFIX}_absent"},
                    "expect_error": "not_found",
                }
            ],
        }
        found_contact = False

        class FakeClient:
            def __init__(self, _settings, *, timeout, max_requests):
                self.requests_sent = 0

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def request(self, operation_id, **_kwargs):
                self.requests_sent += 1
                if operation_id == "CompanyController_get":
                    return SimpleNamespace(status_code=200, data={"id": "test-company"})
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(status_code=200, data=[])
                if operation_id == "CrmExternalIdController_findContactByExternalId":
                    if found_contact:
                        return SimpleNamespace(
                            status_code=200, data={"title": "private-synthetic-contact"}
                        )
                    raise NotFoundError(status_code=404)
                return SimpleNamespace(status_code=200, data={})

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
                allow_sensitive=True,
            )
        row = probe._find_row(report, "CrmExternalIdController_findContactByExternalId")
        self.assertEqual(row["status"], "PASS")
        self.assertEqual(row["category"], "expected_not_found")
        self.assertEqual(row["http_status"], 404)
        self.assertEqual(row["http_attempts"], 1)

        found_contact = True
        with (
            patch.object(probe, "YouGileClient", FakeClient),
            patch.object(probe, "load_local_credentials", return_value=True),
            patch.object(Settings, "from_env", return_value=settings),
        ):
            unexpected_success = await probe.execute_plan(
                plan,
                request_limit=10,
                confirm_disposable_company=True,
                allow_writes=False,
                allow_destructive=False,
                allow_sensitive=True,
            )
        row = probe._find_row(
            unexpected_success, "CrmExternalIdController_findContactByExternalId"
        )
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["category"], "expected_error_not_observed")
        self.assertNotIn("private-synthetic-contact", repr(unexpected_success))

    def test_expected_error_is_limited_to_documented_fixture_probe(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(
                json.dumps(
                    {
                        "company_scope": "disposable_test_company",
                        "fixture_ids": [],
                        "fixture_prefix": PREFIX,
                        "steps": [
                            {
                                "step_id": "invalid_expectation",
                                "operationId": "ProjectController_search",
                                "expect_error": "not_found",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(probe.PlanError):
                probe.load_plan(path)

    def test_plan_loader_allows_expected_crm_not_found(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(
                json.dumps(
                    {
                        "company_scope": "disposable_test_company",
                        "fixture_ids": [],
                        "fixture_prefix": PREFIX,
                        "steps": [
                            {
                                "step_id": "external_lookup",
                                "operationId": "CrmExternalIdController_findContactByExternalId",
                                "query": {"provider": "synthetic", "chatId": f"{PREFIX}_absent"},
                                "expect_error": "not_found",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            loaded = probe.load_plan(path)
        self.assertEqual(loaded["steps"][0]["expect_error"], "not_found")

    def test_plan_preview_records_unavailable_crm_fixture_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "plan.json"
            path.write_text(
                json.dumps(
                    {
                        "company_scope": "disposable_test_company",
                        "fixture_ids": [],
                        "fixture_prefix": PREFIX,
                        "steps": [
                            {
                                "step_id": "crm_blocked",
                                "operationId": "CrmContactPersonsController_create",
                                "blocked_reason": "crm_project_fixture_unavailable",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            plan = probe.load_plan(path)
        report = probe.build_plan_preview(plan, request_limit=10)
        row = probe._find_row(report, "CrmContactPersonsController_create")
        self.assertEqual(row["status"], "BLOCKED")
        self.assertEqual(row["category"], "crm_project_fixture_unavailable")

    async def test_unapproved_active_webhook_blocks_mutations_without_echoing_url(self):
        plan = {
            "company_scope": "disposable_test_company",
            "fixture_ids": [],
            "fixture_prefix": PREFIX,
            "steps": [
                {
                    "step_id": "project_create",
                    "operationId": "ProjectController_create",
                    "body": {"title": PREFIX},
                }
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
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(
                        status_code=200,
                        data=[
                            {
                                "id": "fixture-hook",
                                "url": "https://example.invalid/unknown",
                                "deleted": False,
                                "disabled": False,
                            }
                        ],
                    )
                return SimpleNamespace(status_code=201, data={"id": "created-project"})

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
                allow_destructive=True,
                allow_sensitive=True,
            )

        self.assertEqual(calls, list(probe.PREFLIGHT_OPERATION_IDS))
        self.assertEqual(report["unapproved_active_callbacks"], 1)
        self.assertEqual(
            probe._find_row(report, "ProjectController_create")["category"],
            "unapproved_active_callback",
        )
        self.assertNotIn("example.invalid", repr(report))

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
                if operation_id == "WebhookController_search":
                    return SimpleNamespace(status_code=200, data=[])
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
