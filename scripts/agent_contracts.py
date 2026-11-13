#!/usr/bin/env python3
"""Validate durable contracts and discover applicable authority by changed path.

Only Python's standard library is required.

SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS_DIR = ROOT / "docs" / "contracts"
VALID_AUTHORITIES = frozenset({"draft", "current", "archived"})
REQUIRED_HEADINGS = ("## Intent", "## Invariants", "## Non-goals", "## Verification")
REQUIRED_METADATA = frozenset(
    {"id", "authority", "owner", "applies_to", "superseded_by"}
)


class ContractError(ValueError):
    """Invalid knowledge record or repository instruction surface."""


@dataclass(frozen=True)
class Record:
    id: str
    authority: str
    owner: str
    applies_to: tuple[str, ...]
    superseded_by: str | None
    path: Path


def parse_record(path: Path) -> Record:
    """Read the deliberate, small frontmatter subset without a YAML dependency."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ContractError(f"{path}: expected YAML frontmatter start")
    frontmatter, marker, body = text[4:].partition("\n---\n")
    if not marker:
        raise ContractError(f"{path}: missing frontmatter terminator")

    metadata: dict[str, str] = {}
    for line in frontmatter.splitlines():
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator or not key or key in metadata:
            raise ContractError(f"{path}: malformed/duplicate metadata line: {line!r}")
        metadata[key] = value

    if set(metadata) != REQUIRED_METADATA:
        missing = sorted(REQUIRED_METADATA - metadata.keys())
        extra = sorted(metadata.keys() - REQUIRED_METADATA)
        raise ContractError(f"{path}: frontmatter fields missing={missing}, extra={extra}")

    record_id = metadata["id"]
    if not re.fullmatch(r"YC-[0-9]{3}", record_id):
        raise ContractError(f"{path}: invalid record ID {record_id!r}")
    if not path.name.startswith(record_id + "-"):
        raise ContractError(f"{path}: name must start with {record_id}-")

    authority = metadata["authority"]
    if authority not in VALID_AUTHORITIES:
        raise ContractError(f"{path}: invalid authority {authority!r}")

    owner = metadata["owner"]
    if not owner or not re.fullmatch(r"[a-zA-Z0-9_-]+", owner):
        raise ContractError(f"{path}: owner must be a nonempty identifier")

    try:
        paths = json.loads(metadata["applies_to"])
    except json.JSONDecodeError as exc:
        raise ContractError(f"{path}: applies_to must be a JSON list of globs") from exc
    if not isinstance(paths, list) or not paths or any(
        not isinstance(pattern, str)
        or not pattern
        or pattern == "**"
        or pattern.startswith("/")
        or "\\" in pattern
        or ".." in Path(pattern).parts
        for pattern in paths
    ):
        raise ContractError(f"{path}: invalid applies_to glob list")
    if len(paths) != len(set(paths)):
        raise ContractError(f"{path}: duplicate applies_to patterns")

    successor = metadata["superseded_by"]
    if successor == "null":
        successor = None
    elif not re.fullmatch(r"YC-[0-9]{3}", successor):
        raise ContractError(f"{path}: invalid superseded_by")
    if authority == "archived" and successor is None:
        raise ContractError(f"{path}: archived record needs superseded_by")
    if authority != "archived" and successor is not None:
        raise ContractError(f"{path}: only archived records can have superseded_by")

    for heading in REQUIRED_HEADINGS:
        if heading not in body:
            raise ContractError(f"{path}: missing section {heading}")
    if not re.search(r"\b" + re.escape(record_id) + r"/INV[0-9]+\b", body):
        raise ContractError(f"{path}: no numbered invariants")

    return Record(
        id=record_id,
        authority=authority,
        owner=owner,
        applies_to=tuple(paths),
        superseded_by=successor,
        path=path,
    )


def load_records(root: Path = ROOT) -> list[Record]:
    folder = root / "docs" / "contracts"
    paths = sorted(folder.glob("YC-*.md"))
    if not paths:
        raise ContractError(f"{folder}: no records found")
    records = [parse_record(path) for path in paths]
    by_id: dict[str, Record] = {}
    for record in records:
        if record.id in by_id:
            raise ContractError(f"duplicate record ID {record.id}")
        by_id[record.id] = record

    for record in records:
        if record.superseded_by:
            target = by_id.get(record.superseded_by)
            if target is None or target.authority != "current":
                raise ContractError(
                    f"{record.id}: successor {record.superseded_by} must be current"
                )
    return records


def normalize_path(path: str, root: Path = ROOT) -> str:
    """Require a repository-relative path (no traversal). Files need not yet exist."""
    candidate = Path(path)
    if candidate.is_absolute():
        try:
            candidate = candidate.resolve().relative_to(root.resolve())
        except ValueError as exc:
            raise ContractError("path is outside this repository") from exc
    if not candidate.parts or ".." in candidate.parts:
        raise ContractError(f"unsafe/empty repository path: {path!r}")
    return candidate.as_posix().removeprefix("./")


def applicable(records: list[Record], path: str) -> tuple[list[Record], list[Record]]:
    """Return (binding CURRENT records, informational DRAFT records)."""
    selected = [
        record
        for record in records
        if any(fnmatch.fnmatchcase(path, pattern) for pattern in record.applies_to)
    ]
    current = [record for record in selected if record.authority == "current"]
    draft = [record for record in selected if record.authority == "draft"]
    return current, draft


def check_instruction_files(root: Path = ROOT) -> None:
    """Check that expected multi-layer entry points exist and point to authority."""
    required = (
        "AGENTS.md",
        "CLAUDE.md",
        ".github/copilot-instructions.md",
        "catalog/AGENTS.md",
        "src/yougile_mcp/AGENTS.md",
        "tests/AGENTS.md",
        "docs/AGENTS.md",
        ".agents/README.md",
        ".agents/rules/engineering.md",
        ".agents/rules/api.md",
        ".agents/rules/mcp.md",
        ".agents/rules/security.md",
        ".agents/rules/testing.md",
        ".agents/rules/legal.md",
        ".agents/rules/operations.md",
        ".agents/workflows/change.md",
        ".agents/workflows/decision.md",
        ".agents/workflows/review.md",
        ".agents/skills/add-api-operation/SKILL.md",
        ".agents/skills/add-mcp-tool/SKILL.md",
        ".agents/skills/security-review/SKILL.md",
        ".agents/skills/author-contract/SKILL.md",
    )
    missing = [path for path in required if not (root / path).is_file()]
    if missing:
        raise ContractError("missing agent guidance: " + ", ".join(missing))
    for wrapper in ("CLAUDE.md", ".github/copilot-instructions.md"):
        content = (root / wrapper).read_text(encoding="utf-8")
        if "AGENTS.md" not in content:
            raise ContractError(f"{wrapper}: must refer to canonical AGENTS.md")


def git_changed_paths(base: str, root: Path = ROOT) -> list[str]:
    commands = (
        ["git", "diff", "--name-only", "--diff-filter=ACMR", f"{base}...HEAD"],
        ["git", "diff", "--name-only"],
        ["git", "diff", "--cached", "--name-only"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    )
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        if result.returncode:
            raise ContractError(f"{' '.join(command)} failed: {result.stderr.strip()}")
        paths.update(x for x in result.stdout.splitlines() if x)
    return sorted(paths)


def print_routes(records: list[Record], paths: list[str]) -> None:
    if not paths:
        print("No changed paths")
        return
    for raw_path in paths:
        path = normalize_path(raw_path)
        current, draft = applicable(records, path)
        print(f"\n{path}")
        if current:
            for record in current:
                source = record.path.relative_to(ROOT).as_posix()
                print(f"  CURRENT {record.id}: {source}")
        else:
            print("  CURRENT none (repository-wide AGENTS.md still applies)")
        for record in draft:
            print(f"  DRAFT {record.id}: informational only; NOT authoritative")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Validate records and agent instruction surfaces")
    for_parser = commands.add_parser("for", help="List authoritative records for file paths")
    for_parser.add_argument("paths", nargs="+")
    diff_parser = commands.add_parser("diff", help="List records for git changes since base")
    diff_parser.add_argument("base", help="e.g. origin/main")
    args = parser.parse_args(argv)
    try:
        records = load_records()
        check_instruction_files()
        if args.command == "check":
            counts = {
                authority: sum(r.authority == authority for r in records)
                for authority in sorted(VALID_AUTHORITIES)
            }
            print(f"Agent governance valid: {len(records)} records; {json.dumps(counts)}")
        elif args.command == "for":
            print_routes(records, args.paths)
        else:
            print_routes(records, git_changed_paths(args.base))
    except (ContractError, OSError) as exc:
        print(f"Agent governance error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
