"""Unit tests for execution engine."""

import pytest


class TestExecutionEngine:
    """Test ExecutionEngine."""

    @pytest.mark.asyncio
    async def test_execute_simple_task(self) -> None:
        from app.services.execution.engine import ExecutionEngine, TaskInput

        engine = ExecutionEngine()
        task_input = TaskInput(
            intent="Test task",
            context={"domain": "testing", "task_type": "unit_test"},
        )

        output = await engine.execute_task(task_input)

        assert output.success is True
        assert output.task_id == task_input.task_id
        assert output.result is not None
        assert output.result["intent"] == "Test task"
        assert len(output.steps) > 0
        assert output.duration > 0

    @pytest.mark.asyncio
    async def test_execute_workflow(self) -> None:
        from app.services.execution.engine import ExecutionEngine, TaskInput

        engine = ExecutionEngine()
        task_input = TaskInput(
            intent="Workflow test",
            context={"domain": "devops"},
            workflow=[
                {"name": "build", "action": "execute"},
                {"name": "test", "action": "execute"},
                {"name": "deploy", "action": "execute"},
            ],
        )

        output = await engine.execute_task(task_input)

        assert output.success is True
        assert len(output.steps) == 3
        assert output.result["steps"][0]["step"] == "build"
        assert output.result["steps"][1]["step"] == "test"
        assert output.result["steps"][2]["step"] == "deploy"

    @pytest.mark.asyncio
    async def test_call_tool_not_registered(self) -> None:
        from app.services.execution.engine import ExecutionEngine

        engine = ExecutionEngine()

        with pytest.raises(ValueError, match="not registered"):
            await engine.call_tool("nonexistent_tool", param="value")

    @pytest.mark.asyncio
    async def test_call_tool_success(self) -> None:
        from app.services.execution.engine import ExecutionEngine
        from app.services.execution.tools import Tool, ToolRegistry, ToolResult

        class EchoTool(Tool):
            name = "echo"
            description = "Echo the input"

            async def execute(self, message: str = "") -> ToolResult:
                return ToolResult(success=True, output=message)

        registry = ToolRegistry()
        registry.register(EchoTool())
        engine = ExecutionEngine(tool_registry=registry)

        result = await engine.call_tool("echo", message="hello")
        assert result.success is True
        assert result.output == "hello"

    @pytest.mark.asyncio
    async def test_workflow_with_tool(self) -> None:
        from app.services.execution.engine import ExecutionEngine, TaskInput
        from app.services.execution.tools import Tool, ToolRegistry, ToolResult

        class AdderTool(Tool):
            name = "adder"
            description = "Add two numbers"

            async def execute(self, a: int = 0, b: int = 0) -> ToolResult:
                return ToolResult(success=True, output=a + b)

        registry = ToolRegistry()
        registry.register(AdderTool())
        engine = ExecutionEngine(tool_registry=registry)

        task_input = TaskInput(
            intent="Add numbers",
            workflow=[
                {"name": "add", "tool": "adder", "params": {"a": 3, "b": 5}},
            ],
        )

        output = await engine.execute_task(task_input)
        assert output.success is True
        assert "adder" in output.tools
        assert output.result["steps"][0]["result"]["output"] == 8


class TestExecutionTracer:
    """Test ExecutionTracer."""

    def test_tracer_basic_flow(self) -> None:
        from app.services.execution.trace import ExecutionTracer

        tracer = ExecutionTracer("task-001", "Test intent")

        # Start step
        idx = tracer.start_step("step1", "action1", {"input": "data"})
        assert idx == 0

        # Complete step
        tracer.complete_current_step(outputs={"result": "ok"})

        # Finalize
        record = tracer.finalize(status="completed")

        assert record.final_status == "completed"
        assert len(record.steps) == 1
        assert record.steps[0].status == "completed"
        assert record.steps[0].outputs == {"result": "ok"}

    def test_tracer_tool_recording(self) -> None:
        from app.services.execution.trace import ExecutionTracer

        tracer = ExecutionTracer("task-002", "Tool test")
        tracer.record_tool("http_request", {"url": "http://example.com"}, {"success": True})

        assert "http_request" in tracer.record.tools_used
        assert len(tracer.record.tool_calls) == 1

    def test_tracer_to_dict(self) -> None:
        from app.services.execution.trace import ExecutionTracer

        tracer = ExecutionTracer("task-003", "Dict test")
        tracer.start_step("step1")
        tracer.complete_current_step(outputs="done")
        tracer.finalize(status="completed")

        d = tracer.get_trace_dict()
        assert d["task_id"] == "task-003"
        assert d["intent"] == "Dict test"
        assert d["final_status"] == "completed"
        assert len(d["steps"]) == 1
