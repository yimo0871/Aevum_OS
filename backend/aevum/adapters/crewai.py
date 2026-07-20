"""CrewAI adapter - 让 CrewAI Crew 自动接入 Aevum 经验记忆.

Usage:
    from aevum import AevumClient
    from aevum.adapters.crewai import AevumCrewWrapper

    client = AevumClient(api_key="your-key")
    crew = Crew(agents=[...], tasks=[...])

    # 用 Aevum 包裹
    wrapped = AevumCrewWrapper(crew, client, domain="devops")

    # 执行 -- 自动检索经验 + 自动存储经验
    result = wrapped.kickoff(inputs={"topic": "deploy Flask app"})
    # result.aevum_experiences 包含检索到的历史经验
    # 执行结果已自动存入 Aevum

Architecture:
    kickoff() flow:
        1. Search Aevum for similar experiences (before execution)
        2. Inject experience summaries into crew inputs
        3. Execute crew.kickoff(inputs)
        4. Store execution result as new Experience (after execution)
        5. Attach Aevum metadata to result
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aevum.client import AevumClient

logger = logging.getLogger(__name__)

# crewai 是可选依赖，仅用于类型提示；缺失不影响导入与运行。
try:  # pragma: no cover - 仅类型提示，测试环境无 crewai
    from crewai import Crew  # type: ignore

    _HAS_CREWAI = True
except Exception:  # pragma: no cover
    Crew = None  # type: ignore
    _HAS_CREWAI = False


def _extract_field(result: Any, key: str, default: Any) -> Any:
    """从 CrewOutput / dict 中尽量取一个字段（Mock 安全）.

    优先级：dict 取值 -> CrewOutput.json_dict -> 默认值。
    不会对任意 Mock 属性生效，避免误把 Mock 对象当作真实值。
    """
    if isinstance(result, dict):
        return result.get(key, default)
    json_dict: Any = None
    try:
        json_dict = getattr(result, "json_dict", None)
    except Exception:
        json_dict = None
    if isinstance(json_dict, dict) and key in json_dict:
        return json_dict[key]
    return default


class AevumCrewWrapper:
    """Wraps a CrewAI Crew with Aevum experience memory.

    Before kickoff: searches Aevum, injects experience summaries into inputs.
    After kickoff: stores execution as Experience, attaches metadata to result.

    Args:
        crew: A CrewAI Crew instance.
        client: An authenticated AevumClient instance.
        domain: Domain tag for all experiences (e.g. "devops", "testing").
        task_type: Task type tag (e.g. "deployment", "code_review").
        visibility: Experience visibility (private/community/public).
    """

    def __init__(
        self,
        crew: Any,
        client: AevumClient,
        domain: str = "general",
        task_type: str = "execution",
        visibility: str = "public",
    ) -> None:
        self.crew = crew
        self.client = client
        self.domain = domain
        self.task_type = task_type
        self.visibility = visibility

    # ── 内部工具 ──

    def _extract_task(self, inputs: Any) -> str:
        """从 inputs 中提取任务描述字符串."""
        if inputs is None:
            return ""
        if isinstance(inputs, dict):
            return str(inputs.get("task") or inputs.get("topic") or inputs)
        return str(inputs)

    def _search(self, task: str) -> list[Any]:
        """检索相似经验，失败返回空列表."""
        try:
            return self.client.search(task, domain=self.domain, limit=5)
        except Exception as e:
            logger.warning("[AevumCrewWrapper] Search failed: %s", e)
            return []

    def _inject(self, inputs: Any, experiences: list[Any]) -> dict[str, Any]:
        """将经验摘要注入 inputs（仅对 dict 类型生效）."""
        if not isinstance(inputs, dict):
            inputs = inputs if inputs is not None else {}
        if isinstance(inputs, dict):
            inputs["aevum_experiences"] = [e.summary() for e in experiences]
            inputs["aevum_experience_ids"] = [e.id for e in experiences]
        return inputs

    def _store(self, task: str, result: Any, duration: float, inputs: Any) -> str | None:
        """将执行结果存储为经验，返回经验 id（失败返回 None）."""
        success = _extract_field(result, "success", True)
        what_worked = _extract_field(result, "what_worked", [])
        what_failed = _extract_field(result, "what_failed", [])
        why = _extract_field(result, "why", "")
        tools = _extract_field(result, "tools", [])
        steps = _extract_field(result, "steps", [])
        confidence = _extract_field(result, "confidence", 0.5)
        constraints = inputs.get("constraints", {}) if isinstance(inputs, dict) else {}

        # 后端期望 steps 是 list[dict]，兼容 list[str]
        if steps and isinstance(steps[0], str):
            steps = [{"name": s} for s in steps]

        try:
            new_exp = self.client.create_experience(
                context={
                    "domain": self.domain,
                    "task_type": self.task_type,
                    "constraints": constraints,
                },
                intent=task,
                outcome={"success": success, "metrics": {"duration_s": round(duration, 2)}},
                execution={"steps": steps, "tools": tools, "trace": {}},
                reflection={
                    "what_worked": what_worked,
                    "what_failed": what_failed,
                    "why": why,
                },
                confidence_score=confidence,
                visibility=self.visibility,
            )
            stored_id = new_exp.get("id") if isinstance(new_exp, dict) else None
            logger.info("[AevumCrewWrapper] Experience stored: id=%s", stored_id)
            return stored_id
        except Exception as e:
            logger.error("[AevumCrewWrapper] Failed to store experience: %s", e)
            return None

    def _attach_metadata(
        self,
        result: Any,
        experiences: list[Any],
        stored_id: str | None,
        duration: float,
    ) -> Any:
        """把 Aevum 元数据挂到结果上（dict 合并 / 对象挂属性 / 兜底存 self）."""
        meta = {
            "aevum_experiences": [e.summary() for e in experiences],
            "aevum_experience_ids": [e.id for e in experiences],
            "aevum_experiences_found": len(experiences),
            "aevum_stored_experience_id": stored_id,
            "aevum_duration_s": round(duration, 2),
        }
        # 1) dict 结果：直接合并
        if isinstance(result, dict):
            result.update(meta)
        else:
            # 2) 对象结果：尽量挂属性
            for k, v in meta.items():
                try:
                    setattr(result, k, v)
                except Exception:
                    pass
        # 3) 兜底：同时保留在 self 上，便于无论如何都能取到
        for k, v in meta.items():
            setattr(self, k, v)
        return result

    # ── 公共 API ──

    def kickoff(self, inputs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Execute crew with automatic Aevum memory.

        Args:
            inputs: Crew input variables (e.g. {"topic": "..."}). May contain "task".
            **kwargs: Forwarded to crew.kickoff().

        Returns:
            The crew result, augmented with Aevum metadata.
        """
        task = self._extract_task(inputs)

        # 1 & 2: 检索 + 注入
        experiences = self._search(task)
        inputs = self._inject(inputs, experiences)

        # 3: 执行
        start = time.time()
        result = self.crew.kickoff(inputs=inputs, **kwargs)
        duration = time.time() - start

        # 4: 存储
        stored_id = self._store(task, result, duration, inputs)

        # 5: 元数据
        return self._attach_metadata(result, experiences, stored_id, duration)

    async def kickoff_async(self, inputs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
        """Async version of kickoff. Awaits crew.kickoff_async()."""
        task = self._extract_task(inputs)

        experiences = self._search(task)
        inputs = self._inject(inputs, experiences)

        start = time.time()
        result = await self.crew.kickoff_async(inputs=inputs, **kwargs)
        duration = time.time() - start

        stored_id = self._store(task, result, duration, inputs)
        return self._attach_metadata(result, experiences, stored_id, duration)
