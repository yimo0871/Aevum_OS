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
        community_id: str | None = None,
    ) -> list[PriorityChainResult]:
        """执行四级优先级检索.

        Args:
            query: 搜索查询
            domain: 领域过滤
            task_type: 任务类型过滤
            user_id: 用户 ID（用于用户级检索）
            community_id: 社区 ID（用于社区级检索）

        Returns:
            各优先级的检索结果列表
        """
        chain_results: list[PriorityChainResult] = []
        total_collected = 0

        # ── Priority 1: 用户自身经验 ──
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

        # ── Priority 2: 社区经验 ──
        community_result = PriorityChainResult(level=PriorityLevel.COMMUNITY)
        if community_id:
            community_matches = await self._search_community(
                query, community_id, domain, task_type
            )
            community_result.results = self.ranker.rank(community_matches, query_domain=domain)
            community_result.total_found = len(community_result.results)
            community_result.searched = True
            total_collected += len(community_result.results)
        chain_results.append(community_result)

        if total_collected >= self.min_results:
            return chain_results

        # ── Priority 3: 全球经验 ──
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
        external_result.searched = True
        # MVP: 外部网络检索暂不实现，标记为已搜索但无结果
        chain_results.append(external_result)

        return chain_results

    async def _search_user(
        self, query: str, user_id: str,
        domain: str | None, task_type: str | None,
    ) -> list[MatchResult]:
        """搜索用户自身经验."""
        # MVP: 使用全局搜索（用户隔离在后期实现）
        try:
            return await self.matcher.match_by_vector(
                query, limit=self.max_results, domain=domain, task_type=task_type
            )
        except Exception:
            return await self.matcher.match_by_keywords(
                query, limit=self.max_results, domain=domain
            )

    async def _search_community(
        self, query: str, community_id: str,
        domain: str | None, task_type: str | None,
    ) -> list[MatchResult]:
        """搜索社区经验."""
        # MVP: 与全局搜索相同（社区隔离在后期实现）
        try:
            return await self.matcher.match_by_vector(
                query, limit=self.max_results, domain=domain, task_type=task_type
            )
        except Exception:
            return []

    async def _search_global(
        self, query: str,
        domain: str | None, task_type: str | None,
    ) -> list[MatchResult]:
        """搜索全球经验."""
        try:
            return await self.matcher.match_by_vector(
                query, limit=self.max_results, domain=domain, task_type=task_type
            )
        except Exception:
            return await self.matcher.match_by_keywords(
                query, limit=self.max_results, domain=domain
            )

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
