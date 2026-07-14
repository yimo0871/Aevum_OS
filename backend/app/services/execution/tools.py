"""Tool abstraction - 工具调用接口与注册机制.

Agent 执行层通过 Tool 接口调用外部工具/API/MCP。
每个工具必须注册后才能被执行引擎调用。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


@dataclass
class ToolResult:
    """工具调用结果."""

    success: bool
    output: Any = None
    error: str | None = None
    duration_ms: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata,
        }


class Tool(ABC):
    """工具基类 - 所有可被 Agent 调用的工具必须继承此类.

    属性:
        name: 工具唯一名称
        description: 工具描述
    """

    name: str = ""
    description: str = ""

    @abstractmethod
    async def execute(self, **params: Any) -> ToolResult:
        """执行工具.

        Args:
            **params: 工具参数

        Returns:
            ToolResult: 执行结果
        """
        ...

    def to_dict(self) -> dict:
        """返回工具描述信息."""
        return {
            "name": self.name,
            "description": self.description,
        }


# ── 内置工具 ──


class HTTPRequestTool(Tool):
    """HTTP 请求工具 - 发送 HTTP 请求."""

    name = "http_request"
    description = "向指定 URL 发送 HTTP 请求"

    async def execute(self, url: str, method: str = "GET", headers: dict | None = None,
                      body: dict | None = None, timeout: int = 30) -> ToolResult:
        import time

        import httpx

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers or {},
                    json=body,
                )
                duration = (time.monotonic() - start) * 1000
                return ToolResult(
                    success=response.is_success,
                    output={
                        "status_code": response.status_code,
                        "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
                    },
                    duration_ms=duration,
                    metadata={"url": url, "method": method},
                )
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return ToolResult(success=False, error=str(e), duration_ms=duration)


class ShellCommandTool(Tool):
    """Shell 命令工具 - 执行 Shell 命令（受限环境）."""

    name = "shell_command"
    description = "在受限环境中执行 Shell 命令"

    async def execute(self, command: str, timeout: int = 30, cwd: str | None = None) -> ToolResult:
        import asyncio
        import time

        start = time.monotonic()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            duration = (time.monotonic() - start) * 1000
            success = proc.returncode == 0
            return ToolResult(
                success=success,
                output=stdout.decode("utf-8") if stdout else "",
                error=stderr.decode("utf-8") if stderr and not success else None,
                duration_ms=duration,
                metadata={"command": command, "returncode": proc.returncode},
            )
        except asyncio.TimeoutError:
            duration = (time.monotonic() - start) * 1000
            return ToolResult(success=False, error=f"Command timed out after {timeout}s", duration_ms=duration)
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return ToolResult(success=False, error=str(e), duration_ms=duration)


class FileOperationTool(Tool):
    """文件操作工具 - 读写文件."""

    name = "file_operation"
    description = "读取或写入本地文件系统中的文件"

    async def execute(self, operation: str = "read", path: str = "",
                      content: str | None = None) -> ToolResult:
        import asyncio
        import time

        start = time.monotonic()
        try:
            if operation == "read":
                content = await asyncio.to_thread(lambda: open(path).read())
                duration = (time.monotonic() - start) * 1000
                return ToolResult(success=True, output=content, duration_ms=duration,
                                  metadata={"operation": "read", "path": path})
            elif operation == "write":
                await asyncio.to_thread(lambda: open(path, "w").write(content or ""))
                duration = (time.monotonic() - start) * 1000
                return ToolResult(success=True, output=path, duration_ms=duration,
                                  metadata={"operation": "write", "path": path})
            else:
                return ToolResult(success=False, error=f"Unknown operation: {operation}")
        except Exception as e:
            duration = (time.monotonic() - start) * 1000
            return ToolResult(success=False, error=str(e), duration_ms=duration)


# ── 工具注册表 ──


class ToolRegistry:
    """工具注册表 - 管理所有可用工具."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册工具."""
        if not tool.name:
            raise ValueError("Tool must have a name")
        self._tools[tool.name] = tool
        settings.logger.debug(f"Registered tool: {tool.name}")

    def unregister(self, name: str) -> None:
        """注销工具."""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """获取工具."""
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        """列出所有工具."""
        return [tool.to_dict() for tool in self._tools.values()]

    def has(self, name: str) -> bool:
        """检查工具是否存在."""
        return name in self._tools


# ── 默认注册表（内置工具）──

default_registry = ToolRegistry()
default_registry.register(HTTPRequestTool())
default_registry.register(ShellCommandTool())
default_registry.register(FileOperationTool())
