"""Load and validate the pinned official YouGile OpenAPI 3.0 document."""

# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any, Mapping

from jsonschema import RefResolver, ValidationError
from openapi_schema_validator import OAS30Validator

from .errors import InvalidInputError, UpstreamError

_SPEC_FILE = "openapi-v2.json"
_SOURCE_FILE = "openapi-source.json"


@dataclass(frozen=True)
class Operation:
    operation_id: str
    method: str
    path: str
    effect: str
    parameters: tuple[Mapping[str, Any], ...]
    request_body: Mapping[str, Any] | None
    responses: Mapping[str, Any]
    security: tuple[Mapping[str, Any], ...]


@lru_cache(maxsize=1)
def load_spec() -> dict[str, Any]:
    package = files(__package__)
    raw = package.joinpath(_SPEC_FILE).read_bytes()
    source = json.loads(package.joinpath(_SOURCE_FILE).read_text(encoding="utf-8"))
    if hashlib.sha256(raw).hexdigest() != source["sha256"]:
        raise UpstreamError()
    spec = json.loads(raw)
    if spec.get("openapi") != "3.0.0" or spec.get("info", {}).get("version") != "2.0":
        raise UpstreamError()
    for reference in _references(spec):
        if not reference.startswith("#/"):
            raise UpstreamError()
    return spec


@lru_cache(maxsize=1)
def operations() -> dict[str, Operation]:
    spec = load_spec()
    found: dict[str, Operation] = {}
    for path, path_item in spec["paths"].items():
        path_parameters = path_item.get("parameters", [])
        for method, raw in path_item.items():
            method = method.upper()
            if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                continue
            operation_id = raw.get("operationId")
            if not operation_id or operation_id in found:
                raise UpstreamError()
            parameters = _merge_parameters(path_parameters, raw.get("parameters", []))
            found[operation_id] = Operation(
                operation_id=operation_id,
                method=method,
                path=path,
                effect=operation_effect(operation_id, method),
                parameters=tuple(parameters),
                request_body=raw.get("requestBody"),
                responses=raw.get("responses", {}),
                security=tuple(raw.get("security", spec.get("security", []))),
            )
    return found


def operation_effect(operation_id: str, method: str) -> str:
    if method == "GET" or operation_id in {"getCompanies", "AuthKeyController_search"}:
        return "read"
    if method == "DELETE":
        return "destructive"
    return "write"


def validate_schema(value: Any, schema: Mapping[str, Any], *, request: bool) -> None:
    """Validate against local OAS refs only; never fetch a schema over the network."""
    spec = load_spec()
    resolver = RefResolver.from_schema(spec)
    validator_type = OAS30Validator
    try:
        validator_type(schema, resolver=resolver).validate(value)
    except ValidationError:
        error = InvalidInputError() if request else UpstreamError()
        raise error from None


def _merge_parameters(
    path_parameters: list[Mapping[str, Any]],
    operation_parameters: list[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    merged = {(item["in"], item["name"]): item for item in path_parameters}
    merged.update({(item["in"], item["name"]): item for item in operation_parameters})
    return list(merged.values())


def _references(value: Any):
    if isinstance(value, dict):
        reference = value.get("$ref")
        if isinstance(reference, str):
            yield reference
        for child in value.values():
            yield from _references(child)
    elif isinstance(value, list):
        for child in value:
            yield from _references(child)
