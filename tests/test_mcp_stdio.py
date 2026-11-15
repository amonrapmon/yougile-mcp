"""GEN-231 secure local stdio identity and fail-closed command tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from yougile_mcp.cli import main
from yougile_mcp.config import ConfigError
from yougile_mcp.mcp.factory import build_registry
from yougile_mcp.mcp.stdio import load_identity

COMPANY = "synthetic-stdio-company"


def _identity(**changes):
    original = {
        "subject": "local-test-agent",
        "company_id": COMPANY,
        "scopes": ["yougile.boards.read"],
        "allowed_projects": ["project-1"],
        "company_wide": False,
    }
    original.update(changes)
    return original


class LocalStdioTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "agent.json"
        self._write(_identity())

    def _write(self, value, mode=0o600):
        self.path.write_text(json.dumps(value), encoding="utf-8")
        if os.name == "posix":
            self.path.chmod(mode)

    def test_valid_private_principal(self):
        principal = load_identity(
            str(self.path), company_id=COMPANY, registry=build_registry(),
        )
        self.assertEqual(principal.subject, "local-test-agent")
        self.assertEqual(principal.company_id, COMPANY)
        self.assertEqual(principal.allowed_projects, frozenset({"project-1"}))
        self.assertFalse(principal.company_wide)

    def test_denies_unknown_scope_or_company(self):
        for fields in (
            {"company_id": "other-company"},
            {"scopes": ["yougile.boards.*"]},
            {"scopes": ["yougile.boards.read", "yougile.boards.read"]},
            {"allowed_projects": []},
            {"company_wide": "true"},
            {"subject": "bad actor"},
        ):
            with self.subTest(fields=fields):
                self._write(_identity(**fields))
                with self.assertRaises(ConfigError):
                    load_identity(str(self.path), company_id=COMPANY)
        with self.assertRaises(ConfigError):
            load_identity("relative/path.json", company_id=COMPANY)

    @unittest.skipUnless(os.name == "posix", "POSIX file protection check")
    def test_rejects_world_readable_or_symlink(self):
        self._write(_identity(), mode=0o644)
        with self.assertRaises(ConfigError):
            load_identity(str(self.path), company_id=COMPANY)
        self._write(_identity(), mode=0o600)
        link = Path(self.directory.name) / "linked.json"
        link.symlink_to(self.path)
        with self.assertRaises(ConfigError):
            load_identity(str(link), company_id=COMPANY)

    def test_serve_rejects_missing_identity_and_remote_transport(self):
        values = {
            "MCP_TRANSPORT": "http",
            "YOUGILE_COMPANY_ID": COMPANY, "YOUGILE_API_KEY": "mock-key",
        }
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaises(SystemExit) as denied:
                main(["serve"])
            self.assertEqual(denied.exception.code, 2)
        values["MCP_TRANSPORT"] = "stdio"
        with patch.dict(os.environ, values, clear=True):
            with self.assertRaises(SystemExit) as denied:
                main(["serve"])
            self.assertEqual(denied.exception.code, 2)

    def test_serve_launches_real_stdio_adapter_only_with_private_identity(self):
        async_serve = AsyncMock()
        values = {
            "MCP_TRANSPORT": "stdio", "YOUGILE_COMPANY_ID": COMPANY,
            "YOUGILE_API_KEY": "mock-key",
            "MCP_STDIO_IDENTITY_FILE": str(self.path),
        }
        with patch.dict(os.environ, values, clear=True), patch(
            "yougile_mcp.mcp.stdio.serve_stdio", new=async_serve,
        ):
            self.assertEqual(main(["serve"]), 0)
        async_serve.assert_awaited_once()
        self.assertEqual(async_serve.await_args.args[1].subject, "local-test-agent")


if __name__ == "__main__":
    unittest.main()
