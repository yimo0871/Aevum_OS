"""LangGraph adapter - 让 LangGraph Agent 自动接入 Aevum 经验记忆.

Usage:
    from aevum import AevumClient
    from aevum.adapters.langgraph import AevumRunner

    # 用户已有的 LangGraph
    graph = build_my_graph().compile()

    # 用 Aevum 包裹
    client = AevumClient(api_key="your-key")
    runner = AevumRunner(graph, client, domain="devops")

    # 执行 -- 自动检索经验 + 自动存储经验
    result = runner.invoke({"task": "deploy Flask app"})
    # result["aevum_experiences"] 包含检索到的历史经验
    # 执行结果已自动存入 Aevum

Architecture:
    invoke() flow:
        1. Search Aevum for similar experiences (before execution)
        2. Inject experience summaries into LangGraph state
        3. Execute the LangGraph
        4. Store execution result as new Experience (after execution)
        5. Create improvement relations if similar experiences were found
"""

from __future__ import annotations

import logging
import time
from typing import Any

from aevum.client import AevumClient
from aevum.models import SearchResult

logger = logging.getLogger(__name__)


class AevumRunner:
    """ wraps a LangGraph compiled app with Aevum experience memory.

    Before invoke: searches Aevum, injects experience summaries into state.
    After invoke: stores execution as Experience, creates improvement edges.

    Args:
        graph: A compiled LangGraph runnable (result of graph.compile())
        client: An authenticated AevumClient instance
        domain: Domain tag for all experiences (e.g. "devops", "testing")
        task_type: Task type tag (e.g. "deployment", "code_review")
        visibility: Experience visibility (private/community/public)
    """

    def __init__(
        self,
        graph: Any,
        client: AevumClient,
        domain: str = "general",
        task_type: str = "execution",
        visibility: str = "public",
    ) -> None:
        self.graph = graph
        self.client = client
        self.domain = domain
        self.task_type = task_type
        self.visibility = visibility

    def invoke(self, input: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Execute the graph with automatic Aevum memory.

        Args:
            input: LangGraph input state. Must contain "task" key.
            **kwargs: Passed to graph.invoke()

        Returns:
            The graph result, augmented with "aevum_experiences" and
            "aevum_stored_experience_id" keys.
        """
        task = input.get("task", str(input))

        # 1. Search for similar experiences
        logger.info("[AevumRunner] Searching for similar experiences: '%s'", task[:80])
        try:
            experiences = self.client.search(task, domain=self.domain, limit=5)
        except Exception as e:
            logger.warning("[AevumRunner] Search failed: %s", e)
            experiences = []

        # 2. Inject experiences into state
        if experiences:
            input["aevum_experiences"] = [e.summary() for e in experiences]
            input["aevum_experience_ids"] = [e.id for e in experiences]
            logger.info(
                "[AevumRunner] Found %d similar experiences, injecting into state",
                len(experiences),
            )
        else:
            input["aevum_experiences"] = []
            input["aevum_experience_ids"] = []
            logger.info("[AevumRunner] No similar experiences found")

        # 3. Execute the graph
        start_time = time.time()
        result = self.graph.invoke(input, **kwargs)
        duration = time.time() - start_time

        # 4. Extract results
        success = result.get("success", True)
        what_worked = result.get("what_worked", [])
        what_failed = result.get("what_failed", [])
        why = result.get("why", "")
        tools = result.get("tools", [])
        steps = result.get("steps", [])
        confidence = result.get("confidence", 0.5)

        # 5. Store execution as new experience
        logger.info("[AevumRunner] Storing execution as experience (duration=%.1fs)", duration)
        try:
            new_exp = self.client.create_experience(
                context={
                    "domain": self.domain,
                    "task_type": self.task_type,
                    "constraints": input.get("constraints", {}),
                },
                intent=task,
                outcome={
                    "success": success,
                    "metrics": {"duration_s": round(duration, 2)},
                },
                execution={
                    "steps": steps,
                    "tools": tools,
                    "trace": {},
                },
                reflection={
                    "what_worked": what_worked,
                    "what_failed": what_failed,
                    "why": why,
                },
                confidence_score=confidence,
                visibility=self.visibility,
            )
            stored_id = new_exp.get("id")
            result["aevum_stored_experience_id"] = stored_id
            logger.info("[AevumRunner] Experience stored: id=%s", stored_id)
        except Exception as e:
            logger.error("[AevumRunner] Failed to store experience: %s", e)
            result["aevum_stored_experience_id"] = None

        # 6. Add metadata
        result["aevum_duration_s"] = round(duration, 2)
        result["aevum_experiences_found"] = len(experiences)

        return result

    async def ainvoke(self, input: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """Async version of invoke."""
        task = input.get("task", str(input))

        logger.info("[AevumRunner] (async) Searching: '%s'", task[:80])
        try:
            experiences = self.client.search(task, domain=self.domain, limit=5)
        except Exception as e:
            logger.warning("[AevumRunner] Search failed: %s", e)
            experiences = []

        if experiences:
            input["aevum_experiences"] = [e.summary() for e in experiences]
            input["aevum_experience_ids"] = [e.id for e in experiences]
        else:
            input["aevum_experiences"] = []
            input["aevum_experience_ids"] = []

        start_time = time.time()
        result = await self.graph.ainvoke(input, **kwargs)
        duration = time.time() - start_time

        success = result.get("success", True)
        try:
            new_exp = self.client.create_experience(
                context={"domain": self.domain, "task_type": self.task_type, "constraints": {}},
                intent=task,
                outcome={"success": success, "metrics": {"duration_s": round(duration, 2)}},
                execution={"steps": result.get("steps", []), "tools": result.get("tools", []), "trace": {}},
                reflection={
                    "what_worked": result.get("what_worked", []),
                    "what_failed": result.get("what_failed", []),
                    "why": result.get("why", ""),
                },
                confidence_score=result.get("confidence", 0.5),
                visibility=self.visibility,
            )
            result["aevum_stored_experience_id"] = new_exp.get("id")
        except Exception as e:
            logger.error("[AevumRunner] Store failed: %s", e)
            result["aevum_stored_experience_id"] = None

        result["aevum_duration_s"] = round(duration, 2)
        result["aevum_experiences_found"] = len(experiences)
        return result


def with_experience_context(
    client: AevumClient,
    domain: str = "general",
):
    """Decorator: inject Aevum experiences into a LangGraph node function.

    For fine-grained control over individual nodes.

    Example:
        @with_experience_context(client, domain="devops")
        def plan_node(state):
            # state["aevum_experiences"] contains past experience summaries
            return {"plan": "..."}

    Args:
        client: AevumClient instance
        domain: Domain for experience search
    """

    def decorator(func):
        def wrapper(state: dict[str, Any]) -> dict[str, Any]:
            task = state.get("task", "")
            if task and not state.get("aevum_experiences"):
                try:
                    experiences = client.search(task, domain=domain, limit=3)
                    state["aevum_experiences"] = [e.summary() for e in experiences]
                    state["aevum_experience_ids"] = [e.id for e in experiences]
                except Exception:
                    state["aevum_experiences"] = []
            return func(state)

        return wrapper

    return decorator
