"""No credentials ever appear in doctor output."""

import io
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from yougile_mcp.cli import main


class CliTests(unittest.TestCase):
    def test_doctor_never_prints_credentials(self):
        output = io.StringIO()
        with patch.dict(os.environ, {"YOUGILE_API_KEY": "do-not-print-me"}, clear=True):
            with redirect_stdout(output):
                self.assertEqual(main(["doctor"]), 0)
        self.assertIn("configuration_valid", output.getvalue())
        self.assertNotIn("do-not-print-me", output.getvalue())

    def test_serve_is_explicitly_disabled(self):
        with self.assertRaises(SystemExit) as result:
            main(["serve"])
        self.assertEqual(result.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
