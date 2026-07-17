"""Generic adapter - 框架无关的 Aevum 经验钩子.

适用于没有专属适配器的任意 Agent 框架（AutoGen、LangChain Agent、
自研框架等）。提供 before/after 钩子与上下文管理器两种用法。

Usage:
    from aevum import AevumClient
    from aevum.adapters.generic import AevumHook, AevumContext

    client = AevumClient(api_key="your-key")

    # 方式一：手动 before/after
    hook = AevumHook(client, domain="devops")
    experiences = hook.before_execution("deploy app")
    result = your_framework.run("deploy app")
    hook.after_execution(
        "deploy app", result, success=True, what_worked=["docker"],
    )

    # 方式二：上下文管理器（自动 before/after 生命周期）
    with AevumContext(client, task="deploy app", domain="devops") as ctx:
        # ctx.experiences 含历史经验摘要
        result = your_framework.run("deploy app")
        ctx.record(success=True, what_worked=["docker"])
    # 退出时经验已自动存储

Architecture:
    - before_execution(task): search Aevum -> return list[str] 摘要
    - after_execution(task, result, ...): store experience -> return dict | None
    - AevumContext: __enter__ 调用 before；__exit__ 调用 after
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aevum.client import AevumClient

logger = logging.getLogger(__name__)


def _safe_str(value: Any, max_len: int = 2000) -> str:
    """安全地把任意值转为有限长度字符串（用于 trace 存储）."""
    try:
        s = str(value)
    except Exception:
        s = ""
    return s[:max_len]


class AevumHook:
    """Framework-agnostic Aevum experience hook.

    让任意 Agent 框架在执行前检索经验、执行后沉淀经验，而无需专属适配器。

    Args:
        client: An authenticated AevumClient instance.
        domain: Default domain tag for all experiences.
        task_type: Default task type tag.
        visibility: Default experience visibility (private/community/public).
    """

    def __init__(
        self,
        client: AevumClient,
        domain: str = "general",
        task_type: str = "execution",
        visibility: str = "public",
    ) -> None:
        self.client = client
        self.domain = domain
        self.task_type = task_type
        self.visibility = visibility

    # ── before ──

    def before_execution(
        self,
        task: str,
        domain: str | None = None,
        limit: int = 5,
    ) -> list[str]:
        """执行前检索相似经验，返回经验摘要列表.

        Args:
            task: 任务描述/意图。
            domain: 领域过滤（None 时使用构造时的默认 domain）。
            limit: 返回数量上限。

        Returns:
            按相似度排序的经验摘要字符串列表；检索失败时返回空列表。
        """
        dom = domain or self.domain
        try:
            results = self.client.search(task, domain=dom, limit=limit)
            logger.info(
                "[AevumHook] before_execution found %d experiences for '%s'",
                len(results),
                task[:80],
            )
            return [r.summary() for r in results]
        except Exception as e:
            logger.warning("[AevumHook] before_execution search failed: %s", e)
            return []

    # ── after ──

    def after_execution(
        self,
        task: str,
        result: Any = None,
        domain: str | None = None,
        success: bool = True,
        what_worked: list[str] | None = None,
        what_failed: list[str] | None = None,
        why: str = "",
        tools: list[str] | None = None,
        steps: list[dict] | None = None,
        metrics: dict | None = None,
        confidence: float = 0.5,
        duration_s: float | None = None,
    ) -> dict | None:
        """执行后存储经验，返回创建的经验对象（失败返回 None）.

        Args:
            task: 任务描述/意图。
            result: 执行结果（会被字符串化存入 trace，便于回溯）。
            domain: 领域（None 时使用默认 domain）。
            success: 是否成功。
            what_worked: 有效的做法列表。
            what_failed: 失败的做法列表。
            why: 成败原因。
            tools: 使用的工具列表。
            steps: 执行步骤列表。
            metrics: 额外指标。
            confidence: 置信度 0.0-1.0。
            duration_s: 执行耗时（秒），存入 metrics。

        Returns:
            创建的经验对象（含 id），或 None（存储失败时）。
        """
        dom = domain or self.domain
        outcome_metrics = dict(metrics or {})
        if duration_s is not None:
            outcome_metrics["duration_s"] = round(duration_s, 2)

        try:
            exp = self.client.create_experience(
                context={
                    "domain": dom,
                    "task_type": self.task_type,
                    "constraints": {},
                },
                intent=task,
                outcome={"success": success, "metrics": outcome_metrics},
                execution={
                    "steps": steps or [],
                    "tools": tools or [],
                    "trace": {"result": _safe_str(result)},
                },
                reflection={
                    "what_worked": what_worked or [],
                    "what_failed": what_failed or [],
                    "why": why,
                },
                confidence_score=confidence,
                visibility=self.visibility,
            )
            stored_id = exp.get("id") if isinstance(exp, dict) else None
            logger.info("[AevumHook] after_execution stored experience: id=%s", stored_id)
            return exp
        except Exception as e:
            logger.error("[AevumHook] after_execution store failed: %s", e)
            return None


class AevumContext:
    """上下文管理器：封装 before/after 完整生命周期.

    Example:
        with AevumContext(client, task="deploy app", domain="devops") as ctx:
            # ctx.experiences 含历史经验摘要
            result = my_framework.run("deploy app")
            ctx.record(success=True, what_worked=["docker"])
        # 退出 with 块时经验已自动存储到 Aevum
    """

    def __init__(
        self,
        client: AevumClient,
        task: str,
        domain: str = "general",
        task_type: str = "execution",
        visibility: str = "public",
    ) -> None:
        self._client = client
        self._hook = AevumHook(
            client, domain=domain, task_type=task_type, visibility=visibility
        )
        self.task = task
        self.domain = domain
        self.task_type = task_type
        self.visibility = visibility

        # 进入时填充：历史经验摘要
        self.experiences: list[str] = []
        # 用户可设置：执行结果
        self.result: Any = None
        # 退出时填充：存储后的经验对象
        self.stored_experience: dict | None = None
        self._start_time: float = 0.0

        # 用户通过 record() 填充
        self._success: bool = False
        self._what_worked: list[str] = []
        self._what_failed: list[str] = []
        self._why: str = ""
        self._tools: list[str] = []
        self._steps: list[dict] = []
        self._metrics: dict = {}
        self._confidence: float = 0.5

    def __enter__(self) -> AevumContext:
        self._start_time = time.time()
        self.experiences = self._hook.before_execution(self.task, domain=self.domain)
        return self

    def record(
        self,
        success: bool,
        what_worked: list[str] | None = None,
        what_failed: list[str] | None = None,
        why: str = "",
        tools: list[str] | None = None,
        steps: list[dict] | None = None,
        metrics: dict | None = None,
        confidence: float = 0.5,
    ) -> None:
        """记录执行结果（在 with 块内调用，供退出时存储）."""
        self._success = success
        self._what_worked = what_worked or []
        self._what_failed = what_failed or []
        self._why = why
        self._tools = tools or []
        self._steps = steps or []
        self._metrics = metrics or {}
        self._confidence = confidence

    def record_outcome(self, **kwargs: Any) -> None:
        """record 的别名，兼容 MemoryContext 风格的调用."""
        self.record(**kwargs)

    def __exit__(self, *args: object) -> None:
        duration = time.time() - self._start_time
        self.stored_experience = self._hook.after_execution(
            self.task,
            result=self.result,
            domain=self.domain,
            success=self._success,
            what_worked=self._what_worked,
            what_failed=self._what_failed,
            why=self._why,
            tools=self._tools,
            steps=self._steps,
            metrics=self._metrics,
            confidence=self._confidence,
            duration_s=duration,
        )
