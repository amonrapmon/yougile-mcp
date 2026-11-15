"""Deployment guardrails for DE Docker plus existing HTTPS Traefik."""
from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from yougile_mcp.cloud.server import cloud_serve
from yougile_mcp.config import ConfigError, Settings

ROOT = Path(__file__).resolve().parents[1]


class DockerDeploymentTests(unittest.TestCase):
    def test_dockerfile_includes_cloud_extra(self):
        source = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("uv sync --locked --no-dev --no-editable --extra cloud", source)
        self.assertIn("USER app:app", source)

    def test_compose_never_publishes_application_or_database_ports(self):
        source = (ROOT / "deploy/compose.yml").read_text(encoding="utf-8")
        self.assertNotIn("\n    ports:", source)
        self.assertNotIn("network_mode: host", source)
        self.assertIn("internal: true", source)
        self.assertIn("external: true", source)
        self.assertIn('CLOUD_PRIVATE_CONTAINER_BIND: "1"', source)
        self.assertIn("traefik.enable=true", source)
        self.assertIn("read_only: true", source)
        self.assertIn("cap_drop: [ALL]", source)

    def test_no_real_secrets_in_template(self):
        sample = (ROOT / "deploy/.env.example").read_text(encoding="utf-8")
        self.assertIn("REPLACE_WITH", sample)
        self.assertNotIn("yougile_api_key=", sample.casefold())


class DockerBindTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.config = Settings.from_env({
            "MCP_TRANSPORT": "http", "MCP_HOST": "0.0.0.0",
            "MCP_PUBLIC_URL": "https://mcp.example.test",
        })

    async def test_rejects_open_bind_without_container_flag(self):
        with patch("yougile_mcp.cloud.server.Path.exists", return_value=True):
            with self.assertRaisesRegex(ConfigError, "private Docker bind"):
                await cloud_serve(self.config, env={})

    async def test_rejects_opt_in_outside_docker(self):
        with patch("yougile_mcp.cloud.server.Path.exists", return_value=False):
            with self.assertRaisesRegex(ConfigError, "private Docker bind"):
                await cloud_serve(self.config, env={"CLOUD_PRIVATE_CONTAINER_BIND": "1"})

    async def test_private_container_bind_passes_guard_but_needs_secrets(self):
        with patch("yougile_mcp.cloud.server.Path.exists", return_value=True):
            with self.assertRaisesRegex(ConfigError, "CLOUD_DATABASE_URL"):
                await cloud_serve(self.config, env={"CLOUD_PRIVATE_CONTAINER_BIND": "1"})


if __name__ == "__main__":
    unittest.main()
