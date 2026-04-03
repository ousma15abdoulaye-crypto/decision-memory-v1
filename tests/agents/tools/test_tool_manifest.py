"""Tests — ToolManifest registry."""

from __future__ import annotations

import pytest

from src.agents.tools.tool_manifest import (
    ToolCategory,
    ToolDescriptor,
    ToolManifest,
)


def _desc(
    name: str, cat: ToolCategory = ToolCategory.REGULATORY, det: bool = True
) -> ToolDescriptor:
    return ToolDescriptor(
        name=name, description=f"test {name}", category=cat, deterministic=det
    )


class TestRegistration:
    def test_register_and_get(self) -> None:
        m = ToolManifest()
        d = _desc("foo")
        m.register(d, lambda: 42)
        assert m.get("foo") is d

    def test_duplicate_raises(self) -> None:
        m = ToolManifest()
        m.register(_desc("foo"), lambda: 1)
        with pytest.raises(ValueError, match="already registered"):
            m.register(_desc("foo"), lambda: 2)

    def test_get_missing_returns_none(self) -> None:
        m = ToolManifest()
        assert m.get("nonexistent") is None


class TestInvoke:
    def test_invoke_returns_result(self) -> None:
        m = ToolManifest()
        m.register(_desc("add"), lambda a, b: a + b)
        assert m.invoke("add", a=3, b=4) == 7

    def test_invoke_missing_raises(self) -> None:
        m = ToolManifest()
        with pytest.raises(KeyError, match="not found"):
            m.invoke("ghost")


class TestListTools:
    def test_list_all(self) -> None:
        m = ToolManifest()
        m.register(_desc("a"), lambda: 1)
        m.register(_desc("b"), lambda: 2)
        assert len(m.list_tools()) == 2

    def test_filter_by_category(self) -> None:
        m = ToolManifest()
        m.register(_desc("r1", ToolCategory.REGULATORY), lambda: 1)
        m.register(_desc("e1", ToolCategory.EXTRACTION), lambda: 2)
        reg = m.list_tools(category=ToolCategory.REGULATORY)
        assert len(reg) == 1
        assert reg[0].name == "r1"

    def test_filter_deterministic(self) -> None:
        m = ToolManifest()
        m.register(_desc("det", det=True), lambda: 1)
        m.register(_desc("llm", det=False), lambda: 2)
        det = m.list_tools(deterministic_only=True)
        assert len(det) == 1
        assert det[0].name == "det"

    def test_sorted_by_name(self) -> None:
        m = ToolManifest()
        m.register(_desc("z_tool"), lambda: 1)
        m.register(_desc("a_tool"), lambda: 2)
        names = [t.name for t in m.list_tools()]
        assert names == ["a_tool", "z_tool"]


class TestCount:
    def test_count_empty(self) -> None:
        assert ToolManifest().count() == 0

    def test_count_after_register(self) -> None:
        m = ToolManifest()
        m.register(_desc("x"), lambda: 1)
        assert m.count() == 1


class TestOpenAISchema:
    def test_schema_format(self) -> None:
        m = ToolManifest()
        m.register(_desc("test_tool"), lambda: 1)
        schemas = m.to_openai_tools_schema()
        assert len(schemas) == 1
        assert schemas[0]["type"] == "function"
        assert schemas[0]["function"]["name"] == "test_tool"
        assert "parameters" in schemas[0]["function"]


class TestToolDescriptor:
    def test_frozen(self) -> None:
        d = _desc("immutable")
        with pytest.raises(AttributeError):
            d.name = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        d = ToolDescriptor(name="t", description="d", category=ToolCategory.UTILITY)
        assert d.deterministic is True
        assert d.review_required is False
        assert d.version == "1.0.0"
