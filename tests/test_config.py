"""Configuration and remote-access guard tests."""

import unittest

from yougile_mcp.config import ConfigError, Settings


class SettingsTests(unittest.TestCase):
    def test_safe_defaults(self):
        settings = Settings.from_env({})
        self.assertEqual(settings.transport, "stdio")
        self.assertEqual(settings.host, "127.0.0.1")
        self.assertEqual(settings.auth_mode, "required")
        self.assertFalse(settings.has_api_key)

    def test_no_anonymous_mode(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"MCP_AUTH_MODE": "none"})

    def test_public_bind_requires_https_url(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"MCP_TRANSPORT": "http", "MCP_HOST": "0.0.0.0"})

    def test_http_public_url_must_be_https(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"MCP_PUBLIC_URL": "http://example.com"})

    def test_reject_invalid_port(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"MCP_PORT": "70000"})

    def test_reject_insecure_api_origin(self):
        with self.assertRaises(ConfigError):
            Settings.from_env({"YOUGILE_BASE_URL": "http://example.com"})


if __name__ == "__main__":
    unittest.main()
