"""Pinned public API inventory sanity checks."""

import ast
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

from yougile_mcp.api.client import IMPLEMENTED_OPERATION_IDS

CATALOG = Path(__file__).resolve().parents[1] / "catalog"
ROOT = CATALOG.parent
GENERATOR_PATH = ROOT / "scripts/generate_openapi_catalog.py"
GENERATOR_SPEC = importlib.util.spec_from_file_location("generate_openapi_catalog", GENERATOR_PATH)
assert GENERATOR_SPEC is not None and GENERATOR_SPEC.loader is not None
generator = importlib.util.module_from_spec(GENERATOR_SPEC)
sys.modules[GENERATOR_SPEC.name] = generator
GENERATOR_SPEC.loader.exec_module(generator)
CHECKER_PATH = ROOT / "scripts/check_catalog.py"
CHECKER_SPEC = importlib.util.spec_from_file_location("check_catalog", CHECKER_PATH)
assert CHECKER_SPEC is not None and CHECKER_SPEC.loader is not None
checker = importlib.util.module_from_spec(CHECKER_SPEC)
sys.modules[CHECKER_SPEC.name] = checker
CHECKER_SPEC.loader.exec_module(checker)


class InventoryTests(unittest.TestCase):
    def test_tool_inventory_contains_75_unique_names(self):
        tools = json.loads((CATALOG / "tools-75.json").read_text(encoding="utf-8"))["tools"]
        self.assertEqual(len(tools), 75)
        self.assertEqual(len({item["name"] for item in tools}), 75)
        self.assertTrue(all(item["implementation_status"] == "inventory_only" for item in tools))

    def test_spec_snapshot_and_known_gaps(self):
        source_spec_path = ROOT / "src/yougile_mcp/api/openapi-v2.json"
        source_meta = json.loads(
            (ROOT / "src/yougile_mcp/api/openapi-source.json").read_text(encoding="utf-8")
        )
        source_spec = json.loads(source_spec_path.read_text(encoding="utf-8"))
        operations = json.loads(
            (CATALOG / "openapi-operations.json").read_text(encoding="utf-8")
        )
        rows = operations["operations"]
        gaps = json.loads((CATALOG / "known-gaps.json").read_text(encoding="utf-8"))[
            "operation_ids"
        ]
        self.assertEqual(source_meta["sha256"], hashlib.sha256(source_spec_path.read_bytes()).hexdigest())
        self.assertEqual(source_spec["openapi"], "3.0.0")
        self.assertEqual(source_spec["info"]["version"], "2.0")
        self.assertIsNone(source_spec["info"].get("license"))
        self.assertEqual(len(rows), 72)
        self.assertEqual(len({item["operationId"] for item in rows}), 72)
        self.assertEqual(len(gaps), 5)
        self.assertTrue(set(gaps).issubset({item["operationId"] for item in rows}))
        self.assertEqual({item["status"] for item in rows}, {"mock_tested"})
        self.assertEqual({item["live_evidence"] for item in rows}, {"not_tested", "curl_observed"})
        self.assertEqual(
            {
                item["operationId"]
                for item in rows
                if item["live_evidence"] == "curl_observed"
            },
            {
                "CompanyController_get",
                "FileController_uploadFile",
                "WebhookController_create",
                "WebhookController_put",
                "WebhookController_search",
            },
        )
        self.assertEqual(
            {item["operationId"] for item in rows if item["status"] == "mock_tested"},
            IMPLEMENTED_OPERATION_IDS,
        )
        self.assertEqual(len(IMPLEMENTED_OPERATION_IDS), 72)
        by_id = {item["operationId"]: item for item in rows}
        self.assertEqual(checker._coverage_metadata_errors(rows, source_meta["sha256"]), [])
        overlay_rows = [item for item in rows if item["compatibility_overlay"] is not None]
        self.assertEqual(len(overlay_rows), 6)
        self.assertEqual(
            {item["compatibility_overlay"]["source_sha256"] for item in overlay_rows},
            {source_meta["sha256"]},
        )
        for operation_id in (
            "CompanyController_get",
            "CompanyController_update",
            "FileController_uploadFile",
            "WebhookController_create",
            "WebhookController_put",
            "WebhookController_search",
        ):
            self.assertEqual(by_id[operation_id]["status"], "mock_tested")
            self.assertTrue(by_id[operation_id]["notes"])
        self.assertEqual(by_id["CompanyController_update"]["live_evidence"], "not_tested")
        self.assertIn("no live company update", by_id["CompanyController_update"]["notes"])
        self.assertFalse(any(item["status"] == "implemented" for item in rows))
        self.assertFalse(any(item["status"] == "live_verified" for item in rows))
        self.assertEqual(checker._test_binding_errors(rows, checker._api_test_methods()), [])
        for row in rows:
            if row["status"] == "mock_tested":
                self.assertTrue(
                    all(
                        binding["test_path"].startswith(checker.API_TEST_PATH)
                        for binding in row["test_bindings"]
                    )
                )

    def test_coverage_binding_fails_when_specific_test_is_missing(self):
        row = {
            "operationId": "BoardController_search",
            "status": "mock_tested",
            "test_bindings": [
                {
                    "test_path": "tests/test_api_client.py::ApiClientTests.test_removed_board_search_test",
                    "client_call": "search_boards",
                    "kwargs": {},
                }
            ],
        }
        self.assertEqual(
            checker._test_binding_errors([row], {}),
            [
                "Covered operation test is missing: BoardController_search -> "
                "test_removed_board_search_test"
            ],
        )

    def test_coverage_binding_fails_when_test_does_not_call_operation(self):
        row = {
            "operationId": "BoardController_search",
            "status": "mock_tested",
            "test_bindings": [
                {
                    "test_path": "tests/test_api_client.py::ApiClientTests.test_bound_test",
                    "client_call": "search_boards",
                    "kwargs": {},
                }
            ],
        }
        method = ast.parse("async def test_bound_test():\n    return None\n").body[0]
        self.assertEqual(
            checker._test_binding_errors([row], {"test_bound_test": method}),
            [
                "Test does not call search_boards for BoardController_search: "
                "test_bound_test"
            ],
        )

    def test_coverage_binding_fails_when_operation_case_is_missing(self):
        row = {
            "operationId": "UnknownOperation",
            "method": "GET",
            "path": "/unknown",
            "status": "mock_tested",
            "test_bindings": [
                {
                    "test_path": "tests/test_api_client.py::ApiClientTests.test_operation_contracts",
                    "client_call": "request",
                    "kwargs": {"operation_id": "UnknownOperation"},
                }
            ],
        }
        methods = checker._api_test_methods()
        self.assertEqual(
            checker._test_binding_errors([row], methods),
            ["Operation test case is missing: UnknownOperation"],
        )

    def test_coverage_binding_requires_the_case_to_call_request(self):
        row = {
            "operationId": "UserController_getMe",
            "method": "GET",
            "path": "/api-v2/users/me",
            "effect": "read",
            "status": "mock_tested",
            "test_bindings": [
                {
                    "test_path": "tests/test_api_client.py::ApiClientTests.test_operation_contracts",
                    "client_call": "request",
                    "kwargs": {"operation_id": "UserController_getMe"},
                }
            ],
        }
        method = ast.parse(
            "async def test_operation_contracts():\n"
            "    for operation_id, case in OPERATION_CASES.items():\n"
            "        pass\n"
        ).body[0]
        self.assertEqual(
            checker._test_binding_errors([row], {"test_operation_contracts": method}),
            [
                "Test does not invoke the bound operation case: UserController_getMe"
            ],
        )

    def test_coverage_binding_requires_invalid_case_assertion(self):
        row = {
            "operationId": "UserController_getMe",
            "method": "GET",
            "path": "/api-v2/users/me",
            "effect": "read",
            "status": "mock_tested",
            "test_bindings": [
                {
                    "test_path": "tests/test_api_client.py::ApiClientTests.test_operation_contracts",
                    "client_call": "request",
                    "kwargs": {"operation_id": "UserController_getMe"},
                }
            ],
        }
        method = ast.parse(
            "async def test_operation_contracts():\n"
            "    for operation_id, case in OPERATION_CASES.items():\n"
            "        await client.request(operation_id=operation_id, path=case['path'], "
            "query=case['query'], body=case.get('body'))\n"
        ).body[0]
        self.assertEqual(
            checker._test_binding_errors([row], {"test_operation_contracts": method}),
            ["Test does not invoke the bound operation case: UserController_getMe"],
        )

    def test_upload_coverage_binding_requires_the_multipart_case(self):
        row = {
            "operationId": "FileController_uploadFile",
            "method": "POST",
            "path": "/api-v2/upload-file",
            "effect": "write",
            "status": "mock_tested",
            "test_bindings": [
                {
                    "test_path": "tests/test_api_client.py::ApiClientTests.test_operation_contracts",
                    "client_call": "request",
                    "kwargs": {"operation_id": "FileController_uploadFile"},
                }
            ],
        }
        valid = ast.parse(
            "async def test_operation_contracts():\n"
            "    for operation_id, case in OPERATION_CASES.items():\n"
            "        with self.assertRaises(InvalidInputError):\n"
            "            await client.request(operation_id=operation_id, **case['invalid'])\n"
            "        await client.request(operation_id=operation_id, path=case['path'], "
            "query=case['query'], body=case.get('body'), "
            "multipart_file=case.get('multipart_file'))\n"
        ).body[0]
        missing_multipart = ast.parse(
            "async def test_operation_contracts():\n"
            "    for operation_id, case in OPERATION_CASES.items():\n"
            "        with self.assertRaises(InvalidInputError):\n"
            "            await client.request(operation_id=operation_id, **case['invalid'])\n"
            "        await client.request(operation_id=operation_id, path=case['path'], "
            "query=case['query'], body=case.get('body'))\n"
        ).body[0]
        methods = checker._api_test_methods()
        self.assertEqual(checker._test_binding_errors([row], {**methods, "test_operation_contracts": valid}), [])
        self.assertEqual(
            checker._test_binding_errors([row], {**methods, "test_operation_contracts": missing_multipart}),
            ["Test does not invoke the bound operation case: FileController_uploadFile"],
        )

    def test_coverage_metadata_does_not_mistake_curl_for_sdk_verification(self):
        row = {
            "operationId": "WebhookController_search",
            "status": "mock_tested",
            "live_evidence": "curl_observed",
            "compatibility_overlay": {"version": "2026-11-14.1", "source_sha256": "pinned"},
        }
        self.assertEqual(checker._coverage_metadata_errors([row], "pinned"), [])
        row["status"] = "live_verified"
        self.assertEqual(
            checker._coverage_metadata_errors([row], "pinned"),
            ["live_verified operation lacks Python-client evidence: WebhookController_search"],
        )
        row["status"] = "mock_tested"
        row["compatibility_overlay"]["source_sha256"] = "stale"
        self.assertEqual(
            checker._coverage_metadata_errors([row], "pinned"),
            ["Compatibility overlay is not tied to the pinned source: WebhookController_search"],
        )

    def test_coverage_matrix_is_generated_from_the_pinned_source(self):
        spec = json.loads((ROOT / "src/yougile_mcp/api/openapi-v2.json").read_text(encoding="utf-8"))
        source = json.loads(
            (ROOT / "src/yougile_mcp/api/openapi-source.json").read_text(encoding="utf-8")
        )
        actual = json.loads((CATALOG / "openapi-operations.json").read_text(encoding="utf-8"))
        self.assertEqual(generator.build_catalog(spec, source), actual)


if __name__ == "__main__":
    unittest.main()
