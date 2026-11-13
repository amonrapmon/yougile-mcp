"""Pinned public API inventory sanity checks."""

import json
import hashlib
import importlib.util
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
        self.assertEqual(
            {item["status"] for item in rows}, {"discovered", "mock_tested"}
        )
        self.assertEqual(
            {item["operationId"] for item in rows if item["status"] == "mock_tested"},
            IMPLEMENTED_OPERATION_IDS,
        )
        self.assertFalse(any(item["status"] == "implemented" for item in rows))
        self.assertFalse(any(item["status"] == "live_verified" for item in rows))
        for row in rows:
            if row["status"] == "mock_tested":
                self.assertIn("tests/test_api_client.py", row["test_paths"])

    def test_coverage_matrix_is_generated_from_the_pinned_source(self):
        spec = json.loads((ROOT / "src/yougile_mcp/api/openapi-v2.json").read_text(encoding="utf-8"))
        source = json.loads(
            (ROOT / "src/yougile_mcp/api/openapi-source.json").read_text(encoding="utf-8")
        )
        actual = json.loads((CATALOG / "openapi-operations.json").read_text(encoding="utf-8"))
        self.assertEqual(generator.build_catalog(spec, source), actual)


if __name__ == "__main__":
    unittest.main()
