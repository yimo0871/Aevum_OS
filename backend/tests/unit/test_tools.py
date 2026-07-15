"""Unit tests for execution tools."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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

    def test_result_with_metadata(self) -> None:
        from app.services.execution.tools import ToolResult

        result = ToolResult(
            success=True, output="ok",
            metadata={"key": "value"}, duration_ms=50.0,
        )
        d = result.to_dict()
        assert d["metadata"] == {"key": "value"}
        assert d["duration_ms"] == 50.0


class TestToolBaseClass:
    """Test Tool base class methods."""

    def test_to_dict(self) -> None:
        from app.services.execution.tools import Tool, ToolResult

        class MyTool(Tool):
            name = "my_tool"
            description = "My custom tool"

            async def execute(self, **params):
                return ToolResult(success=True)

        tool = MyTool()
        d = tool.to_dict()
        assert d["name"] == "my_tool"
        assert d["description"] == "My custom tool"

    def test_default_registry_has_tools(self) -> None:
        from app.services.execution.tools import default_registry

        assert default_registry.has("http_request")
        assert default_registry.has("shell_command")
        assert default_registry.has("file_operation")

    def test_registry_get_nonexistent(self) -> None:
        from app.services.execution.tools import ToolRegistry

        registry = ToolRegistry()
        assert registry.get("nonexistent") is None

    def test_unregister_nonexistent_silently(self) -> None:
        from app.services.execution.tools import ToolRegistry

        registry = ToolRegistry()
        registry.unregister("nonexistent")  # should not raise


class TestHTTPRequestTool:
    """Test HTTPRequestTool."""

    @pytest.mark.asyncio
    async def test_success_json_response(self) -> None:
        from app.services.execution.tools import HTTPRequestTool

        tool = HTTPRequestTool()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"result": "ok"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await tool.execute(url="http://example.com/api", method="GET")

        assert result.success is True
        assert result.output["status_code"] == 200
        assert result.output["body"] == {"result": "ok"}
        assert result.metadata["url"] == "http://example.com/api"
        assert result.metadata["method"] == "GET"

    @pytest.mark.asyncio
    async def test_success_text_response(self) -> None:
        from app.services.execution.tools import HTTPRequestTool

        tool = HTTPRequestTool()

        mock_response = MagicMock()
        mock_response.is_success = True
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.text = "Hello world"

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await tool.execute(url="http://example.com", method="POST", body={"key": "val"})

        assert result.success is True
        assert result.output["body"] == "Hello world"

    @pytest.mark.asyncio
    async def test_error_response(self) -> None:
        from app.services.execution.tools import HTTPRequestTool

        tool = HTTPRequestTool()

        mock_response = MagicMock()
        mock_response.is_success = False
        mock_response.status_code = 500
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"error": "server error"}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.request = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await tool.execute(url="http://example.com")

        assert result.success is False
        assert result.output["status_code"] == 500

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        from app.services.execution.tools import HTTPRequestTool

        tool = HTTPRequestTool()

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_cls.return_value = mock_client

            result = await tool.execute(url="http://example.com")

        assert result.success is False
        assert "Connection refused" in result.error
        assert result.duration_ms > 0


class TestShellCommandTool:
    """Test ShellCommandTool."""

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        from app.services.execution.tools import ShellCommandTool

        tool = ShellCommandTool()

        mock_proc = AsyncMock()
        mock_proc.returncode = 0
        mock_proc.communicate = AsyncMock(return_value=(b"output", b""))

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
            result = await tool.execute(command="echo hello")

        assert result.success is True
        assert result.output == "output"
        assert result.error is None
        assert result.metadata["command"] == "echo hello"
        assert result.metadata["returncode"] == 0

    @pytest.mark.asyncio
    async def test_failure(self) -> None:
        from app.services.execution.tools import ShellCommandTool

        tool = ShellCommandTool()

        mock_proc = AsyncMock()
        mock_proc.returncode = 1
        mock_proc.communicate = AsyncMock(return_value=(b"", b"command not found"))

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
            result = await tool.execute(command="badcommand")

        assert result.success is False
        assert result.error == "command not found"

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        from app.services.execution.tools import ShellCommandTool

        tool = ShellCommandTool()

        mock_proc = AsyncMock()
        mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

        with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
            result = await tool.execute(command="sleep 100", timeout=1)

        assert result.success is False
        assert "timed out" in result.error

    @pytest.mark.asyncio
    async def test_exception(self) -> None:
        from app.services.execution.tools import ShellCommandTool

        tool = ShellCommandTool()

        with patch("asyncio.create_subprocess_shell", side_effect=Exception("Spawn error")):
            result = await tool.execute(command="test")

        assert result.success is False
        assert "Spawn error" in result.error


class TestFileOperationTool:
    """Test FileOperationTool."""

    @pytest.mark.asyncio
    async def test_read_success(self, tmp_path) -> None:
        from app.services.execution.tools import FileOperationTool

        test_file = tmp_path / "test.txt"
        test_file.write_text("file content")

        tool = FileOperationTool()
        result = await tool.execute(operation="read", path=str(test_file))

        assert result.success is True
        assert result.output == "file content"
        assert result.metadata["operation"] == "read"

    @pytest.mark.asyncio
    async def test_write_success(self, tmp_path) -> None:
        from app.services.execution.tools import FileOperationTool

        test_file = tmp_path / "output.txt"

        tool = FileOperationTool()
        result = await tool.execute(operation="write", path=str(test_file), content="written data")

        assert result.success is True
        assert result.metadata["operation"] == "write"
        assert test_file.read_text() == "written data"

    @pytest.mark.asyncio
    async def test_unknown_operation(self) -> None:
        from app.services.execution.tools import FileOperationTool

        tool = FileOperationTool()
        result = await tool.execute(operation="delete", path="/some/path")

        assert result.success is False
        assert "Unknown operation" in result.error

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self) -> None:
        from app.services.execution.tools import FileOperationTool

        tool = FileOperationTool()
        result = await tool.execute(operation="read", path="/nonexistent/file.txt")

        assert result.success is False
        assert result.error is not None
