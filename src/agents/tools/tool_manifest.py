"""
ToolManifest — registre central des tools exposables a un agent LLM.

Chaque tool est deterministe (callable sans LLM) ou LLM-assisted
(review_required=True). Un agent peut filtrer par mode et invoquer
les tools via le registre sans connaitre l'implementation.

Conforme a DMS_VIVANT_V2_FREEZE.md §6.2.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum, unique
from typing import Any


@unique
class ToolCategory(StrEnum):
    REGULATORY = "regulatory"
    EXTRACTION = "extraction"
    EVALUATION = "evaluation"
    MEMORY = "memory"
    UTILITY = "utility"


@dataclass(frozen=True)
class ToolDescriptor:
    """Metadata for a registered tool."""

    name: str
    description: str
    category: ToolCategory
    deterministic: bool = True
    review_required: bool = False
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"


class ToolManifest:
    """
    Central registry for agent-callable tools.

    Thread-safe for reads after initial registration.
    Registration is NOT thread-safe (assumed to happen at import time).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDescriptor] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    def register(
        self,
        descriptor: ToolDescriptor,
        handler: Callable[..., Any],
    ) -> None:
        if descriptor.name in self._tools:
            raise ValueError(f"Tool '{descriptor.name}' already registered")
        self._tools[descriptor.name] = descriptor
        self._handlers[descriptor.name] = handler

    def get(self, name: str) -> ToolDescriptor | None:
        return self._tools.get(name)

    def invoke(self, name: str, **kwargs: Any) -> Any:
        if name not in self._handlers:
            raise KeyError(f"Tool '{name}' not found in manifest")
        return self._handlers[name](**kwargs)

    def list_tools(
        self,
        *,
        category: ToolCategory | None = None,
        deterministic_only: bool = False,
    ) -> list[ToolDescriptor]:
        tools = list(self._tools.values())
        if category is not None:
            tools = [t for t in tools if t.category == category]
        if deterministic_only:
            tools = [t for t in tools if t.deterministic]
        return sorted(tools, key=lambda t: t.name)

    def count(self) -> int:
        return len(self._tools)

    def to_openai_tools_schema(self) -> list[dict[str, Any]]:
        """Export as OpenAI-compatible function calling schema."""
        schemas: list[dict[str, Any]] = []
        for t in self._tools.values():
            schemas.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.input_schema
                        or {"type": "object", "properties": {}},
                    },
                }
            )
        return schemas
