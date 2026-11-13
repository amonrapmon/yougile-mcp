"""Negative and positive structural architecture checks."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts/architecture_guard.py"
spec = importlib.util.spec_from_file_location("architecture_guard", SOURCE)
assert spec is not None and spec.loader is not None
guard = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = guard
spec.loader.exec_module(guard)


class ArchitectureGuardTests(unittest.TestCase):
    def test_repository_passes(self):
        self.assertEqual(guard.main(), 0)

    def test_mcp_tool_cannot_import_http_client(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / guard.MCP_LAYER
            folder.mkdir(parents=True)
            (folder / "get_task.py").write_text(
                "from httpx import AsyncClient\n", encoding="utf-8"
            )
            failures = guard.tool_http_import_violations(root)
            self.assertEqual(len(failures), 1)
            self.assertIn("httpx", failures[0])

    def test_nested_tool_cannot_import_requests(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / guard.MCP_LAYER / "smart"
            folder.mkdir(parents=True)
            (folder / "batch.py").write_text(
                "import requests.sessions\n", encoding="utf-8"
            )
            failures = guard.tool_http_import_violations(root)
            self.assertEqual(len(failures), 1)

    def test_shared_api_client_import_is_allowed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            folder = root / guard.MCP_LAYER
            folder.mkdir(parents=True)
            (folder / "get_task.py").write_text(
                "from yougile_mcp.api.client import YouGileClient\n",
                encoding="utf-8",
            )
            self.assertEqual(guard.tool_http_import_violations(root), [])

    def test_detect_protocol_version_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            refs = root / "docs/references"
            refs.mkdir(parents=True)
            base = json.loads(
                (ROOT / "docs/references/standards.json").read_text(encoding="utf-8")
            )
            base["pins"]["mcp_protocol"]["version"] = "2025-11-25"
            (refs / "standards.json").write_text(
                json.dumps(base), encoding="utf-8"
            )
            catalog = root / "catalog"
            catalog.mkdir()
            (catalog / "openapi-operations.json").write_text(
                (ROOT / "catalog/openapi-operations.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            failures = guard.standards_violations(root)
            self.assertTrue(any("mcp_protocol" in msg for msg in failures))


if __name__ == "__main__":
    unittest.main()
