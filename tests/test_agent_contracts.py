"""Contract authority, routing and instruction surface invariants."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "agent_contracts.py"
spec = importlib.util.spec_from_file_location("agent_contracts", SCRIPT)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)

sys.modules[spec.name] = module
spec.loader.exec_module(module)


class GovernanceTests(unittest.TestCase):
    def test_all_repo_records_validate(self):
        records = module.load_records()
        self.assertEqual(len(records), 5)
        self.assertEqual({r.id for r in records}, {f"YC-{i:03d}" for i in range(1, 6)})
        self.assertTrue(all(r.authority == "current" for r in records))

    def test_scoped_routing(self):
        records = module.load_records()
        current, draft = module.applicable(records, "src/yougile_mcp/config.py")
        self.assertEqual(
            {r.id for r in current}, {"YC-001", "YC-002", "YC-003", "YC-004"}
        )
        self.assertEqual(draft, [])
        current, _ = module.applicable(records, "docs/contracts/YC-005-governance.md")
        self.assertEqual({r.id for r in current}, {"YC-005"})

    def test_draft_never_becomes_authority(self):
        base = module.load_records()[0]
        draft = module.Record(
            id="YC-099",
            authority="draft",
            owner="maintainer",
            applies_to=("src/**",),
            superseded_by=None,
            path=base.path,
        )
        current, informational = module.applicable([draft], "src/example.py")
        self.assertEqual(current, [])
        self.assertEqual(informational, [draft])

    def test_malformed_spec_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            f = Path(name) / "YC-099-test.md"
            f.write_text("---\nid: YC-099\n---\n# missing fields\n", encoding="utf-8")
            with self.assertRaises(module.ContractError):
                module.parse_record(f)

    def test_no_path_traversal(self):
        with self.assertRaises(module.ContractError):
            module.normalize_path("../private.key")

    def test_agent_surfaces_exist(self):
        module.check_instruction_files()

    def test_check_command_passes(self):
        self.assertEqual(module.main(["check"]), 0)


if __name__ == "__main__":
    unittest.main()
