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
        self.assertIsNone(settings.yougile_api_key)

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

    def test_api_key_is_available_but_redacted_from_repr(self):
        settings = Settings.from_env({"YOUGILE_API_KEY": "secret-token"})
        self.assertEqual(settings.yougile_api_key.reveal(), "secret-token")
        self.assertTrue(settings.has_api_key)
        self.assertNotIn("secret-token", repr(settings))
        self.assertNotIn("secret-token", repr(settings.yougile_api_key))

    def test_api_origin_rejects_paths_and_embedded_credentials(self):
        for origin in (
            "https://example.com/api-v2",
            "https://user:password@example.com",
            "https://example.com/?token=secret",
        ):
            with self.subTest(origin=origin), self.assertRaises(ConfigError):
                Settings.from_env({"YOUGILE_BASE_URL": origin})

    def test_rejects_invalid_origin_port_and_api_key_header_injection(self):
        for values in (
            {"YOUGILE_BASE_URL": "https://example.com:99999"},
            {"YOUGILE_API_KEY": "secret\r\nInjected: value"},
        ):
            with self.subTest(values=values), self.assertRaises(ConfigError):
                Settings.from_env(values)


if __name__ == "__main__":
    unittest.main()
