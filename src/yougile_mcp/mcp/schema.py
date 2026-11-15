"""Convert compatible OAS 3.0 schema objects into JSON Schema 2020-12.

Pinned vendor snapshot is never modified; only local recursive definitions resolve.
SPDX-License-Identifier: AGPL-3.0-only
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

from jsonschema import Draft202012Validator
from ..api.errors import UpstreamError

_IGNORED = {"nullable", "example", "examples", "discriminator", "xml",
            "externalDocs", "readOnly", "writeOnly", "deprecated"}


def convert_oas(schema: Mapping[str, Any], definitions: Mapping[str, Any]) -> dict[str, Any]:
    needed: set[str] = set()
    result = _convert(schema, needed)
    resolved: dict[str, Any] = {}
    while needed - resolved.keys():
        name = sorted(needed - resolved.keys())[0]
        if name not in definitions:
            raise UpstreamError()
        resolved[name] = {}
        resolved[name] = _convert(definitions[name], needed)
    if resolved:
        result["$defs"] = {name: resolved[name] for name in sorted(resolved)}
    Draft202012Validator.check_schema(result)
    return result


def _convert(schema: Any, needed: set[str]) -> dict[str, Any]:
    if not isinstance(schema, Mapping):
        raise UpstreamError()
    result: dict[str, Any] = {}
    for key, value in schema.items():
        if key in _IGNORED or key.startswith("x-"):
            continue
        if key == "$ref":
            prefix = "#/components/schemas/"
            if not isinstance(value, str) or not value.startswith(prefix):
                raise UpstreamError()
            name = value[len(prefix):]
            if not name or "/" in name or "~" in name:
                raise UpstreamError()
            needed.add(name)
            result[key] = "#/$defs/" + name
        elif key in {"properties", "patternProperties"}:
            result[key] = {name: _convert(part, needed) for name, part in value.items()}
        elif key in {"items", "additionalProperties", "not"} and isinstance(value, Mapping):
            result[key] = _convert(value, needed)
        elif key in {"oneOf", "anyOf", "allOf"}:
            result[key] = [_convert(part, needed) for part in value]
        elif key in {"exclusiveMinimum", "exclusiveMaximum"} and isinstance(value, bool):
            if value:
                source = "minimum" if key == "exclusiveMinimum" else "maximum"
                if source not in schema:
                    raise UpstreamError()
                result[key] = schema[source]
                result.pop(source, None)
        elif key not in {"minimum", "maximum"} or not (
            schema.get("exclusiveMinimum" if key == "minimum" else "exclusiveMaximum") is True
        ):
            result[key] = deepcopy(value)
    if schema.get("nullable") is True:
        if "type" in result and isinstance(result["type"], str):
            result["type"] = [result["type"], "null"]
        else:
            result = {"anyOf": [result, {"type": "null"}]}
    return result


def assemble_schema(schema: Mapping[str, Any], definitions: Mapping[str, Any]) -> dict[str, Any]:
    return convert_oas(schema, definitions)
