"""Aevum SDK 客户端 - Agent 经验记忆层核心."""

from __future__ import annotations

from typing import Any

import httpx

from aevum.models import Experience, SearchResult


class AevumClient:
    """Aevum 经验记忆客户端.

    让 Agent 在执行任务前检索相似经验，执行后自动沉淀经验。

    Args:
        api_key: Agent API Key（从管理后台获取）
        base_url: Aevum 服务地址，默认 http://localhost:8000
        timeout: 请求超时秒数，默认 30

    Example:
        >>> client = AevumClient(api_key="ak_xxx")
        >>> results = client.search("optimize database query")
        >>> for r in results:
        ...     print(r.summary())
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "X-API-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=timeout,
        )

    # ── 检索 ──

    def search(
        self,
        query: str,
        domain: str | None = None,
        task_type: str | None = None,
        limit: int = 5,
    ) -> list[SearchResult]:
        """检索相似经验.

        在执行任务前调用，获取历史上相似场景的经验。

        Args:
            query: 任务描述/意图
            domain: 领域过滤（如 frontend, backend, devops）
            task_type: 任务类型过滤（如 deployment, testing）
            limit: 返回数量上限

        Returns:
            按相似度排序的经验列表
        """
        body: dict[str, Any] = {"query": query, "limit": limit}
        if domain:
            body["domain"] = domain
        if task_type:
            body["task_type"] = task_type

        resp = self._client.post("/api/v1/retrieval/search", json=body)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [SearchResult.from_api(item) for item in data]
        return []

    def recommend(
        self,
        query: str,
        domain: str | None = None,
        limit: int = 3,
    ) -> list[SearchResult]:
        """获取经验推荐（综合检索 + 排序）.

        与 search 类似，但使用推荐端点，会综合信任评分和衰减因子。

        Returns:
            按推荐度排序的经验列表
        """
        params: dict[str, Any] = {"query": query, "limit": limit}
        if domain:
            params["domain"] = domain

        resp = self._client.get("/api/v1/retrieval/recommend", params=params)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list):
            return [SearchResult.from_api(item) for item in data]
        return []

    # ── 存储 ──

    def create_experience(
        self,
        context: dict[str, Any],
        intent: str,
        outcome: dict[str, Any] | None = None,
        execution: dict[str, Any] | None = None,
        reflection: dict[str, Any] | None = None,
        reusable_patterns: list[dict] | None = None,
        confidence_score: float = 0.5,
        visibility: str = "private",
    ) -> dict:
        """存储一条经验.

        在任务执行完成后调用，将执行过程沉淀为可复用经验。

        Args:
            context: 上下文，必须包含 domain 和 task_type
            intent: 任务意图描述
            outcome: 执行结果，必须包含 success (bool)
            execution: 执行过程 (steps/tools/trace)
            reflection: 反思 (what_worked/what_failed/why)
            reusable_patterns: 可复用模式
            confidence_score: 置信度 0.0-1.0
            visibility: 可见性 private/community/public

        Returns:
            创建的经验对象（含 id）
        """
        exp = Experience(
            context=context,
            intent=intent,
            outcome=outcome or {"success": False, "metrics": {}},
            execution=execution or {"steps": [], "tools": [], "trace": {}},
            reflection=reflection or {"what_worked": [], "what_failed": [], "why": ""},
            reusable_patterns=reusable_patterns or [],
            confidence_score=confidence_score,
            visibility=visibility,
        )
        resp = self._client.post("/api/v1/experiences", json=exp.to_api())
        resp.raise_for_status()
        return resp.json()

    def get_experience(self, experience_id: str) -> dict:
        """获取单条经验详情."""
        resp = self._client.get(f"/api/v1/experiences/{experience_id}")
        resp.raise_for_status()
        return resp.json()

    def list_experiences(
        self,
        page: int = 1,
        page_size: int = 20,
        domain: str | None = None,
    ) -> dict:
        """列出经验."""
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if domain:
            params["domain"] = domain
        resp = self._client.get("/api/v1/experiences", params=params)
        resp.raise_for_status()
        return resp.json()

    # ── 高级：自动记忆 ──

    def memory(
        self,
        task: str,
        domain: str = "general",
        task_type: str = "execution",
        constraints: dict | None = None,
        visibility: str = "private",
    ) -> MemoryContext:
        """创建自动记忆上下文.

        在任务执行前检索经验，在执行后自动沉淀经验。

        Example:
            with client.memory("deploy app", domain="devops") as mem:
                results = my_agent.execute(task)
                mem.record_outcome(
                    success=True,
                    what_worked=["docker build", "kubectl apply"],
                    tools=["docker", "kubectl"],
                )
            # 经验已自动存储

        Args:
            task: 任务描述
            domain: 领域
            task_type: 任务类型
            constraints: 约束条件
            visibility: 经验可见性

        Returns:
            MemoryContext 上下文管理器
        """
        return MemoryContext(
            client=self,
            task=task,
            domain=domain,
            task_type=task_type,
            constraints=constraints or {},
            visibility=visibility,
        )

    # ── 工具 ──

    def close(self) -> None:
        """关闭客户端连接."""
        self._client.close()

    def __enter__(self) -> AevumClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class MemoryContext:
    """自动记忆上下文管理器.

    进入时自动检索相似经验，退出时自动存储新经验。
    """

    def __init__(
        self,
        client: AevumClient,
        task: str,
        domain: str,
        task_type: str,
        constraints: dict,
        visibility: str,
    ) -> None:
        self._client = client
        self._task = task
        self._domain = domain
        self._task_type = task_type
        self._constraints = constraints
        self._visibility = visibility

        # 检索到的历史经验（进入时填充）
        self.relevant_experiences: list[SearchResult] = []

        # 执行结果（用户填充）
        self._success: bool = False
        self._what_worked: list[str] = []
        self._what_failed: list[str] = []
        self._why: str = ""
        self._tools: list[str] = []
        self._steps: list[dict] = []
        self._metrics: dict = {}
        self._confidence: float = 0.5

    def __enter__(self) -> MemoryContext:
        # 执行前：检索相似经验
        try:
            self.relevant_experiences = self._client.search(
                query=self._task,
                domain=self._domain,
                limit=5,
            )
        except Exception:
            # 检索失败不阻塞执行
            self.relevant_experiences = []
        return self

    def record_outcome(
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
        """记录执行结果（在 with 块内调用）."""
        self._success = success
        self._what_worked = what_worked or []
        self._what_failed = what_failed or []
        self._why = why
        self._tools = tools or []
        self._steps = steps or []
        self._metrics = metrics or {}
        self._confidence = confidence

    def __exit__(self, *args: object) -> None:
        # 执行后：自动存储经验
        try:
            self._client.create_experience(
                context={
                    "domain": self._domain,
                    "task_type": self._task_type,
                    "constraints": self._constraints,
                },
                intent=self._task,
                outcome={"success": self._success, "metrics": self._metrics},
                execution={
                    "steps": self._steps,
                    "tools": self._tools,
                    "trace": {},
                },
                reflection={
                    "what_worked": self._what_worked,
                    "what_failed": self._what_failed,
                    "why": self._why,
                },
                confidence_score=self._confidence,
                visibility=self._visibility,
            )
        except Exception:
            # 存储失败不影响主流程
            pass
