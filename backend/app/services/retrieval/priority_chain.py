"""Priority chain - 四级优先级检索链.

所有任务在执行前，必须按以下优先级检索经验，外部网络仅作为兜底：

    优先级 1: 用户自身经验图谱     ← 最优先
    优先级 2: 社区经验图谱
    优先级 3: 全球经验图谱
    优先级 4: 外部网络数据          ← 仅兜底

逐级检索，上级有结果则不查下级。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience
from app.services.retrieval.external import ExternalResult, get_external_search_provider
from app.services.retrieval.matcher import ExperienceMatcher, MatchResult
from app.services.retrieval.ranker import ExperienceRanker, RankedResult


class PriorityLevel(IntEnum):
    """检索优先级."""

    USER = 1      # 用户自身经验
    COMMUNITY = 2  # 社区经验
    GLOBAL = 3    # 全球经验
    EXTERNAL = 4  # 外部网络（兜底）


@dataclass
class PriorityChainResult:
    """优先级链检索结果."""

    level: PriorityLevel
    results: list[RankedResult] = field(default_factory=list)
    total_found: int = 0
    searched: bool = False

    def to_dict(self) -> dict:
        return {
            "level": self.level.name,
            "level_value": int(self.level),
            "total_found": self.total_found,
            "searched": self.searched,
            "results": [r.to_dict() for r in self.results],
        }


class PriorityChain:
    """四级优先级检索链.

    按优先级逐级检索经验，上级有足够结果则不查下级。
    """

    def __init__(
        self,
        session: AsyncSession,
        min_results: int = 3,
        max_results: int = 10,
    ) -> None:
        self.session = session
        self.matcher = ExperienceMatcher(session)
        self.ranker = ExperienceRanker()
        self.min_results = min_results
        self.max_results = max_results

    async def search(
        self,
        query: str,
        domain: str | None = None,
        task_type: str | None = None,
        user_id: str | None = None,
        community_ids: list[str] | None = None,
    ) -> list[PriorityChainResult]:
        """执行四级优先级检索.

        Args:
            query: 搜索查询
            domain: 领域过滤
            task_type: 任务类型过滤
            user_id: 用户 ID（用于用户级检索）
            community_ids: 用户所属社区 ID 列表（用于社区级检索隔离）

        Returns:
            各优先级的检索结果列表
        """
        chain_results: list[PriorityChainResult] = []
        total_collected = 0

        # ── Priority 1: 用户自身经验（所有可见性，因为是自己的）──
        user_result = PriorityChainResult(level=PriorityLevel.USER)
        if user_id:
            user_matches = await self._search_user(
                query, user_id, domain, task_type
            )
            user_result.results = self.ranker.rank(user_matches, query_domain=domain)
            user_result.total_found = len(user_result.results)
            user_result.searched = True
            total_collected += len(user_result.results)
        chain_results.append(user_result)

        if total_collected >= self.min_results:
            return chain_results

        # ── Priority 2: 社区经验（visibility=community|public，社区隔离，排除自己的）──
        community_result = PriorityChainResult(level=PriorityLevel.COMMUNITY)
        if community_ids:
            community_matches = await self._search_community(
                query, community_ids, domain, task_type, exclude_user_id=user_id
            )
            community_result.results = self.ranker.rank(community_matches, query_domain=domain)
            community_result.total_found = len(community_result.results)
            community_result.searched = True
            total_collected += len(community_result.results)
        chain_results.append(community_result)

        if total_collected >= self.min_results:
            return chain_results

        # ── Priority 3: 全球经验（visibility=public）──
        global_result = PriorityChainResult(level=PriorityLevel.GLOBAL)
        global_matches = await self._search_global(query, domain, task_type)
        global_result.results = self.ranker.rank(global_matches, query_domain=domain)
        global_result.total_found = len(global_result.results)
        global_result.searched = True
        total_collected += len(global_result.results)
        chain_results.append(global_result)

        if total_collected >= self.min_results:
            return chain_results

        # ── Priority 4: 外部网络（兜底）──
        external_result = PriorityChainResult(level=PriorityLevel.EXTERNAL)
        external_matches = await self._search_external(query, domain, task_type)
        external_result.results = self.ranker.rank(external_matches, query_domain=domain)
        external_result.total_found = len(external_result.results)
        external_result.searched = True
        total_collected += len(external_result.results)
        chain_results.append(external_result)

        return chain_results

    async def _search_user(
        self, query: str, user_id: str,
        domain: str | None, task_type: str | None,
    ) -> list[MatchResult]:
        """搜索用户自身经验（所有可见性级别，因为是自己的）."""
        if not user_id:
            return []
        try:
            return await self.matcher.match_by_vector(
                query, limit=self.max_results, domain=domain,
                task_type=task_type, user_id=user_id
            )
        except Exception:
            return []

    async def _search_community(
        self, query: str, community_ids: list[str],
        domain: str | None, task_type: str | None,
        exclude_user_id: str | None = None,
    ) -> list[MatchResult]:
        """搜索社区经验（社区隔离 + visibility=community|public，排除自己的经验）.

        community 可见性的经验仅返回用户所属社区内的；
        public 可见性的经验不受社区限制。
        """
        try:
            return await self.matcher.match_by_vector(
                query, limit=self.max_results, domain=domain, task_type=task_type,
                visibility_levels=["community", "public"],
                exclude_user_id=exclude_user_id,
                community_ids=community_ids,
            )
        except Exception:
            return []

    async def _search_global(
        self, query: str,
        domain: str | None, task_type: str | None,
    ) -> list[MatchResult]:
        """搜索全球经验（visibility=public）."""
        try:
            return await self.matcher.match_by_vector(
                query, limit=self.max_results, domain=domain, task_type=task_type,
                visibility_levels=["public"],
            )
        except Exception:
            return await self.matcher.match_by_keywords(
                query, limit=self.max_results, domain=domain,
                visibility_levels=["public"],
            )

    async def _search_external(
        self, query: str,
        domain: str | None, task_type: str | None,
    ) -> list[MatchResult]:
        """搜索外部网络（兜底）.

        通过 ExternalSearchProvider 搜索外部网络资源。
        如果未配置外部搜索 API，返回空结果（优雅降级）。
        外部结果被包装为轻量 Experience 对象以统一排序。
        """
        provider = get_external_search_provider()
        try:
            results = await provider.search(query, limit=self.max_results)
        except Exception:
            return []

        matches: list[MatchResult] = []
        for r in results:
            # 将外部结果包装为轻量 Experience 对象
            exp = Experience(
                id=None,
                context={"domain": domain or "external", "task_type": task_type or "search"},
                intent=r.title,
                outcome={"success": True, "metrics": {}},
                execution={"steps": [], "tools": [], "trace": {}},
                reflection={"what_worked": [], "what_failed": [], "why": r.snippet},
                reusable_patterns=[],
                confidence_score=0.3,  # 外部结果默认低置信度
                provenance={"source": r.source, "url": r.url, "external": True},
                version=1,
                evaluation_status="evaluated",
                visibility="public",
            )
            # 外部结果相似度为 0（无法计算向量相似度），使用 snippet 匹配度作为近似
            similarity = 0.1
            matches.append(MatchResult(
                experience=exp,
                similarity=similarity,
                matched_fields=["external"],
            ))

        return matches

    def get_best_results(
        self, chain_results: list[PriorityChainResult], limit: int = 5
    ) -> list[RankedResult]:
        """从优先级链结果中提取最佳结果.

        合并所有级别的结果，按总分排序，取 top N。
        """
        all_results: list[RankedResult] = []
        for chain_result in chain_results:
            all_results.extend(chain_result.results)

        all_results.sort(key=lambda r: r.total_score, reverse=True)
        return all_results[:limit]
