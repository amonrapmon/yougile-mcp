#!/usr/bin/env python3
"""Offline inventory checks, not runtime coverage verification.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import json
import hashlib
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
    matrix = load("openapi-operations.json")
    operations = matrix["operations"]
    gaps = set(load("known-gaps.json")["operation_ids"])
    names = {item["name"] for item in tools}
    ids = {item["operationId"] for item in operations}
    spec_path = ROOT / "src/yougile_mcp/api/openapi-v2.json"
    source = json.loads(
        (ROOT / "src/yougile_mcp/api/openapi-source.json").read_text(encoding="utf-8")
    )
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    spec_operations = {
        (operation["operationId"], method.upper(), path)
        for path, path_item in spec["paths"].items()
        for method, operation in path_item.items()
        if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}
    }
    matrix_operations = {
        (item["operationId"], item["method"], item["path"]) for item in operations
    }

    if len(tools) != 75 or len(names) != 75:
        raise SystemExit("Expected exactly 75 distinct PR #5 tool names")
    if spec.get("openapi") != "3.0.0" or spec.get("info", {}).get("version") != "2.0":
        raise SystemExit("Unexpected YouGile OpenAPI/version axis")
    if hashlib.sha256(spec_path.read_bytes()).hexdigest() != source.get("sha256"):
        raise SystemExit("Pinned official OpenAPI checksum does not match")
    if len(operations) != len(ids) or matrix_operations != spec_operations:
        raise SystemExit("Coverage matrix differs from the pinned official operations")
    if gaps != GAPS or not gaps.issubset(ids):
        raise SystemExit("Known gaps do not match the pinned snapshot")
    if any(item["status"] not in {"discovered", "implemented", "mock_tested", "live_verified", "excluded_with_reason"} for item in operations):
        raise SystemExit("Unknown operation coverage status")
    if any(item["status"] == "excluded_with_reason" and not item.get("notes") for item in operations):
        raise SystemExit("Every excluded operation needs a reason")
    for item in operations:
        if item["status"] in {"implemented", "mock_tested", "live_verified"}:
            test_paths = item.get("test_paths", [])
            if not test_paths or any(not (ROOT / path).is_file() for path in test_paths):
                raise SystemExit(f"Covered operation has no test path: {item['operationId']}")
    if any(item["implementation_status"] != "inventory_only" for item in tools):
        raise SystemExit("Foundation catalog must not claim implementation")

    counts = {status: sum(item["status"] == status for item in operations) for status in (
        "discovered", "implemented", "mock_tested", "live_verified", "excluded_with_reason"
    )}
    print(f"Inventory validated: {len(names)} tool names, {len(ids)} official API operations")
    print(f"Coverage statuses: {json.dumps(counts, sort_keys=True)}")
    print(f"Known missing mappings in PR #5: {len(gaps)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
