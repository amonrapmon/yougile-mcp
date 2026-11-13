"""Initial authorization model must fail closed."""

import unittest

from yougile_mcp.policy import Principal, authorize


class PolicyTests(unittest.TestCase):
    def test_anonymous_denied(self):
        self.assertFalse(authorize(None, "tasks", "read"))

    def test_scope_is_required(self):
        principal = Principal("agent-a", frozenset(), frozenset({"tasks"}))
        self.assertFalse(authorize(principal, "tasks", "read"))

    def test_domain_is_required(self):
        principal = Principal(
            "agent-a", frozenset({"yougile.tasks.read"}), frozenset({"projects"})
        )
        self.assertFalse(authorize(principal, "tasks", "read"))

    def test_only_explicit_scope_grants_access(self):
        principal = Principal("agent-a", frozenset({"yougile.tasks.read"}), frozenset({"tasks"}))
        self.assertTrue(authorize(principal, "tasks", "read"))
        self.assertFalse(authorize(principal, "tasks", "write"))

    def test_unknown_access_denied(self):
        principal = Principal("agent-a", frozenset({"*"}), frozenset({"tasks"}))
        self.assertFalse(authorize(principal, "tasks", "setup_only"))


if __name__ == "__main__":
    unittest.main()
