"""Administrative command-line entry point.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os

from . import __version__
from .config import ConfigError, Settings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="yougile-mcp")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Validate config without contacting YouGile")
    commands.add_parser("serve", help="Run authenticated local stdio MCP only")
    args = parser.parse_args(argv)

    try:
        config = Settings.from_env()
    except ConfigError as exc:
        parser.exit(2, f"Invalid configuration: {exc}\n")

    if args.command == "serve":
        # A local child process inherits one protected identity from its
        # launcher. Streamable HTTP requires separate OAuth review and remains
        # disabled even when MCP_TRANSPORT=http is configured.
        if config.transport != "stdio":
            parser.exit(2, "Remote MCP transport is disabled pending authorization review.\n")
        if not config.company_id_set or not config.has_api_key:
            parser.exit(2, "Local stdio requires a YouGile company and API key.\n")
        from .mcp.factory import build_registry
        from .mcp.stdio import load_identity, serve_stdio

        try:
            principal = load_identity(
                os.environ.get("MCP_STDIO_IDENTITY_FILE"),
                company_id=config.company_id,
                registry=build_registry(),
            )
            asyncio.run(serve_stdio(config, principal))
        except ConfigError as exc:
            parser.exit(2, f"Local stdio configuration rejected: {exc}\n")
        except KeyboardInterrupt:
            return 130
        return 0

    print(
        json.dumps(
            {
                "status": "configuration_valid",
                "package_version": __version__,
                "transport_requested": config.transport,
                "authentication": config.auth_mode,
                "yougile_key_present": config.has_api_key,
                "yougile_company_id_present": config.company_id_set,
                "mcp_implementation": "sdk_internal_and_local_stdio",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
