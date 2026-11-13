"""Administrative command-line entry point.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import argparse
import json

from . import __version__
from .config import ConfigError, Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="yougile-mcp")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Validate config without contacting YouGile")
    commands.add_parser("serve", help="Reserved: server is not yet implemented")
    args = parser.parse_args(argv)

    if args.command == "serve":
        parser.exit(
            2,
            "The MCP transport is not implemented in the foundation commit. "
            "Do not publish an HTTP port. See GEN-218 and GEN-220.\n",
        )

    try:
        config = Settings.from_env()
    except ConfigError as exc:
        parser.exit(2, f"Invalid configuration: {exc}\n")

    print(
        json.dumps(
            {
                "status": "configuration_valid",
                "package_version": __version__,
                "transport_requested": config.transport,
                "authentication": config.auth_mode,
                "yougile_key_present": config.has_api_key,
                "yougile_company_id_present": config.company_id_set,
                "mcp_implementation": "not_implemented",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
