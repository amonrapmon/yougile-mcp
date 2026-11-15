"""Historical 75-tool inventory parity against verified 72 REST operations."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

from yougile_mcp.api.spec import operations
from yougile_mcp.mcp.factory import build_registry

ROOT = Path(__file__).resolve().parents[1]
LEGACY = json.loads((ROOT / "catalog/tools-75.json").read_text(encoding="utf-8"))
PARITY = json.loads((ROOT / "catalog/legacy-75-parity.json").read_text(encoding="utf-8"))


class LegacyParityTests(unittest.TestCase):
    def test_every_historical_name_is_classified_once(self):
        originals = [entry["name"] for entry in LEGACY["tools"]]
        mapped = [entry["legacy_name"] for entry in PARITY["tools"]]
        self.assertEqual(len(originals), 75)
        self.assertEqual(len(mapped), 75)
        self.assertEqual(len(set(mapped)), 75)
        self.assertEqual(set(originals), set(mapped))
        self.assertEqual(
            {kind: sum(item["kind"] == kind for item in PARITY["tools"])
             for kind in PARITY["summary"]},
            PARITY["summary"],
        )

    def test_referenced_operations_are_real_and_registered(self):
        defined = set(operations())
        registered = {item.operation_id for item in build_registry().list()}
        self.assertEqual(defined, registered)
        for entry in PARITY["tools"]:
            with self.subTest(name=entry["legacy_name"]):
                self.assertIn(entry["kind"], {
                    "direct", "smart", "write_adapter", "needs_api_verification",
                })
                self.assertTrue(entry["operation_ids"])
                for operation_id in entry["operation_ids"]:
                    self.assertIn(operation_id, defined)
                if entry["kind"] != "direct":
                    self.assertTrue(entry.get("note"))

    def test_direct_coverage_does_not_claim_smart_parity(self):
        self.assertEqual(PARITY["summary"], {
            "direct": 66,
            "smart": 2,
            "write_adapter": 5,
            "needs_api_verification": 2,
        })


if __name__ == "__main__":
    unittest.main()
