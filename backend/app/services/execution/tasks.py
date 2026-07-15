"""Celery async tasks for experience pipeline."""

from __future__ import annotations

from app.celery_app import celery_app


@celery_app.task(name="execute_task_async", bind=True)
def execute_task_async(self, intent: str, context: dict | None = None,
                       constraints: dict | None = None,
                       workflow: list[dict] | None = None,
                       user_id: str | None = None) -> dict:
    """异步执行 8 步经验流水线.

    Args:
        intent: 任务意图
        context: 任务上下文
        constraints: 约束条件
        workflow: 工作流定义
        user_id: 用户 ID（用于数据隔离）

    Returns:
        dict: 流水线结果
    """
    import asyncio

    from app.core.database import async_session_factory
    from app.services.execution.pipeline import ExperiencePipeline

    async def _run() -> dict:
        async with async_session_factory() as session:
            pipeline = ExperiencePipeline(session)
            result = await pipeline.run(
                intent=intent,
                context=context,
                constraints=constraints,
                workflow=workflow,
                user_id=user_id,
            )
            return result.model_dump()

    return asyncio.run(_run())
