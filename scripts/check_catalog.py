#!/usr/bin/env python3
"""Offline inventory checks, not runtime coverage verification.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAPS = {
    "TaskController_getLog",
    "UserController_getMe",
    "ChatMessageController_typing",
    "CrmContactPersonsController_create",
    "CrmExternalIdController_findContactByExternalId",
}


def load(name: str) -> dict:
    return json.loads((ROOT / "catalog" / name).read_text(encoding="utf-8"))


def main() -> int:
    tools = load("tools-75.json")["tools"]
    operations = load("openapi-operations.json")["operations"]
    gaps = set(load("known-gaps.json")["operation_ids"])
    names = {item["name"] for item in tools}
    ids = {item["operationId"] for item in operations}

    if len(tools) != 75 or len(names) != 75:
        raise SystemExit("Expected exactly 75 distinct PR #5 tool names")
    if len(operations) != 70 or len(ids) != 70:
        raise SystemExit("Expected exactly 70 distinct operations in pinned OpenAPI snapshot")
    if gaps != GAPS or not gaps.issubset(ids):
        raise SystemExit("Known gaps do not match the pinned snapshot")
    if any(item["implementation_status"] != "inventory_only" for item in tools):
        raise SystemExit("Foundation catalog must not claim implementation")

    print(f"Inventory validated: {len(names)} tool names, {len(ids)} API operations")
    print(f"Known missing mappings in PR #5: {len(gaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
