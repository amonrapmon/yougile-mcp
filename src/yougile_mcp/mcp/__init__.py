"""Policy-gated MCP tool catalog and execution engine (transport-independent)."""

# SPDX-License-Identifier: AGPL-3.0-only

from .factory import ToolDescriptor, ToolRegistry, build_registry

__all__ = ["ToolDescriptor", "ToolRegistry", "build_registry"]
