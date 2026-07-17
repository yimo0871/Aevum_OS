"""Real-time experience streaming via Server-Sent Events (SSE).

通过 SSE 实时推送新增的经验对象。MVP 采用轮询方式（每 2 秒），
相较于 WebSocket 实现更简单且兼容性更好。
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.experience import Experience

router = APIRouter()


async def fetch_new_experiences(
    session,
    since: datetime,
    domain: str | None = None,
    limit: int = 50,
) -> list[Experience]:
    """查询指定时间点之后创建的新经验.

    Args:
        session: 数据库会话
        since: 起始时间（仅返回此时间之后创建的经验）
        domain: 领域过滤（None 表示不过滤）
        limit: 返回数量上限

    Returns:
        按创建时间升序排列的经验列表
    """
    query = select(Experience).where(
        Experience.created_at > since,
        Experience.status == "active",
    )
    if domain:
        query = query.where(Experience.context["domain"].astext == domain)
    query = query.order_by(Experience.created_at.asc()).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


def format_sse_event(experience: Experience) -> str:
    """将经验对象格式化为 SSE data 事件.

    格式: ``data: {"id": ..., "intent": ..., "domain": ...}\\n\\n``
    """
    context = experience.context if isinstance(experience.context, dict) else {}
    data = {
        "id": str(experience.id) if experience.id else "",
        "intent": experience.intent or "",
        "domain": context.get("domain"),
    }
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


async def experience_event_stream(
    session_factory=async_session_factory,
    domain: str | None = None,
    poll_interval: float = 2.0,
    max_iterations: int | None = None,
) -> AsyncGenerator[str, None]:
    """生成实时经验的 SSE 事件流.

    定期轮询数据库，推送创建时间晚于上次检查点的新经验。

    Args:
        session_factory: 异步会话工厂（每次轮询创建新会话）
        domain: 领域过滤
        poll_interval: 轮询间隔（秒）
        max_iterations: 最大轮询次数（None 表示无限，用于测试限制）
    """
    since = datetime.now(timezone.utc)
    iteration = 0

    while max_iterations is None or iteration < max_iterations:
        async with session_factory() as session:
            experiences = await fetch_new_experiences(session, since, domain)

        for exp in experiences:
            if exp.created_at and exp.created_at > since:
                since = exp.created_at
            yield format_sse_event(exp)

        iteration += 1
        if max_iterations is None or iteration < max_iterations:
            await asyncio.sleep(poll_interval)


def _sse_headers() -> dict[str, str]:
    """返回 SSE 标准响应头."""
    return {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }


@router.get(
    "/stream/experiences",
    summary="实时经验流",
    description="通过 SSE 实时推送新增的经验对象，每 2 秒轮询一次数据库。",
)
async def stream_experiences() -> StreamingResponse:
    """SSE 流 - 实时推送新经验."""
    return StreamingResponse(
        experience_event_stream(async_session_factory),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )


@router.get(
    "/stream/domain/{domain}",
    summary="按领域实时经验流",
    description="通过 SSE 实时推送指定领域的新增经验对象。",
)
async def stream_experiences_by_domain(domain: str) -> StreamingResponse:
    """SSE 流 - 按领域过滤的实时经验推送."""
    return StreamingResponse(
        experience_event_stream(async_session_factory, domain=domain),
        media_type="text/event-stream",
        headers=_sse_headers(),
    )
