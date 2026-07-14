"""Execution API routes - 任务执行接口."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db_session
from app.schemas.execution import TaskSubmitRequest, TaskStatusResponse
from app.services.execution.engine import ExecutionEngine, TaskInput
from app.services.execution.pipeline import ExperiencePipeline

router = APIRouter()


@router.post(
    "/tasks",
    response_model=TaskStatusResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交任务（同步执行）",
    description="提交任务并同步执行 8 步经验流水线。返回执行状态和生成的经验 ID。",
)
async def submit_task(
    request: TaskSubmitRequest,
    session: AsyncSession = Depends(get_db_session),
) -> TaskStatusResponse:
    """提交任务 - 同步执行 8 步流水线."""
    pipeline = ExperiencePipeline(session)
    result = await pipeline.run(
        intent=request.intent,
        context=request.context,
        constraints=request.constraints,
    )

    if result.status == "invalid":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Task executed but no Experience generated: {result.error}",
        )

    # 构建响应
    from datetime import datetime, timezone

    return TaskStatusResponse(
        id=UUID(result.task_id) if result.task_id else UUID(int=0),
        status=result.status,
        intent=request.intent,
        experience_id=UUID(result.experience_id) if result.experience_id else None,
        pipeline_state={s.model_dump() for s in result.steps} if False else
            {str(s.step): s.model_dump() for s in result.steps},
        duration=result.total_duration_ms / 1000,
        error=result.error,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


@router.post(
    "/tasks/async",
    response_model=dict,
    status_code=status.HTTP_202_ACCEPTED,
    summary="提交任务（异步执行）",
    description="提交任务异步执行，返回 Celery 任务 ID。使用 GET /execution/tasks/{task_id} 查询状态。",
)
async def submit_task_async(request: TaskSubmitRequest) -> dict:
    """提交任务 - 异步执行（通过 Celery）."""
    from app.services.execution.tasks import execute_task_async

    task = execute_task_async.delay(
        intent=request.intent,
        context=request.context,
        constraints=request.constraints,
    )

    return {
        "task_id": task.id,
        "status": "queued",
        "intent": request.intent,
        "message": "Task queued for async execution. Use GET /execution/tasks/{task_id}/status to check.",
    }


@router.get(
    "/tasks/{task_id}/status",
    response_model=dict,
    summary="查询异步任务状态",
    description="查询 Celery 异步任务的执行状态和结果。",
)
async def get_async_task_status(task_id: str) -> dict:
    """查询异步任务状态."""
    from app.services.execution.tasks import execute_task_async

    result = execute_task_async.AsyncResult(task_id)

    response = {
        "task_id": task_id,
        "status": result.status,
    }

    if result.ready():
        if result.successful():
            response["result"] = result.result
        elif result.failed():
            response["error"] = str(result.result)

    return response


@router.get(
    "/tools",
    response_model=list[dict],
    summary="列出可用工具",
    description="列出所有已注册的工具。",
)
async def list_tools() -> list[dict]:
    """列出所有可用工具."""
    from app.services.execution.tools import default_registry

    return default_registry.list_tools()
