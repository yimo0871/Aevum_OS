"""Unit tests for execution tools."""

import pytest


class TestToolRegistry:
    """Test ToolRegistry."""

    def test_register_and_get(self) -> None:
        from app.services.execution.tools import ToolRegistry, Tool, ToolResult

        class FakeTool(Tool):
            name = "fake_tool"
            description = "A fake tool for testing"

            async def execute(self, **params):
                return ToolResult(success=True, output=params)

        registry = ToolRegistry()
        registry.register(FakeTool())

        assert registry.has("fake_tool")
        tool = registry.get("fake_tool")
        assert tool is not None
        assert tool.name == "fake_tool"

    def test_unregister(self) -> None:
        from app.services.execution.tools import ToolRegistry, Tool, ToolResult

        class FakeTool(Tool):
            name = "temp_tool"
            description = "Temporary tool"

            async def execute(self, **params):
                return ToolResult(success=True)

        registry = ToolRegistry()
        registry.register(FakeTool())
        assert registry.has("temp_tool")

        registry.unregister("temp_tool")
        assert not registry.has("temp_tool")

    def test_list_tools(self) -> None:
        from app.services.execution.tools import default_registry

        tools = default_registry.list_tools()
        assert len(tools) >= 3
        names = [t["name"] for t in tools]
        assert "http_request" in names
        assert "shell_command" in names
        assert "file_operation" in names

    def test_register_empty_name_raises(self) -> None:
        from app.services.execution.tools import ToolRegistry, Tool, ToolResult

        class NoNameTool(Tool):
            name = ""
            description = "No name"

            async def execute(self, **params):
                return ToolResult(success=True)

        registry = ToolRegistry()
        with pytest.raises(ValueError, match="Tool must have a name"):
            registry.register(NoNameTool())


class TestToolResult:
    """Test ToolResult dataclass."""

    def test_success_result(self) -> None:
        from app.services.execution.tools import ToolResult

        result = ToolResult(success=True, output={"key": "value"}, duration_ms=100.0)
        d = result.to_dict()
        assert d["success"] is True
        assert d["output"] == {"key": "value"}
        assert d["duration_ms"] == 100.0
        assert d["error"] is None

    def test_error_result(self) -> None:
        from app.services.execution.tools import ToolResult

        result = ToolResult(success=False, error="Something went wrong")
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "Something went wrong"
