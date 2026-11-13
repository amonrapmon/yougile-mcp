"""Pinned public API inventory sanity checks."""

import json
import unittest
from pathlib import Path

CATALOG = Path(__file__).resolve().parents[1] / "catalog"


class InventoryTests(unittest.TestCase):
    def test_tool_inventory_contains_75_unique_names(self):
        tools = json.loads((CATALOG / "tools-75.json").read_text(encoding="utf-8"))["tools"]
        self.assertEqual(len(tools), 75)
        self.assertEqual(len({item["name"] for item in tools}), 75)
        self.assertTrue(all(item["implementation_status"] == "inventory_only" for item in tools))

    def test_spec_snapshot_and_known_gaps(self):
        operations = json.loads(
            (CATALOG / "openapi-operations.json").read_text(encoding="utf-8")
        )["operations"]
        gaps = json.loads((CATALOG / "known-gaps.json").read_text(encoding="utf-8"))[
            "operation_ids"
        ]
        self.assertEqual(len(operations), 70)
        self.assertEqual(len({item["operationId"] for item in operations}), 70)
        self.assertEqual(len(gaps), 5)
        self.assertTrue(set(gaps).issubset({item["operationId"] for item in operations}))


if __name__ == "__main__":
    unittest.main()
