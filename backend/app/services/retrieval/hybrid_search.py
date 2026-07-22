"""Hybrid search - 混合检索（向量 + BM25 全文检索）.

融合向量语义相似度和关键词全文检索，提升检索精度。
final_score = alpha * vector_score + (1 - alpha) * bm25_score
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.retrieval.matcher import ExperienceMatcher

logger = logging.getLogger(__name__)


@dataclass
class HybridSearchResult:
    """混合检索结果."""

    experience_id: str
    vector_score: float  # 归一化后的向量相似度 [0, 1]
    keyword_score: float  # BM25 分数归一化 [0, 1]
    hybrid_score: float  # 融合分数
    experience: object  # Experience ORM 对象

    def to_dict(self) -> dict:
        return {
            "experience_id": self.experience_id,
            "vector_score": round(self.vector_score, 4),
            "keyword_score": round(self.keyword_score, 4),
            "hybrid_score": round(self.hybrid_score, 4),
        }


class HybridSearcher:
    """混合检索器 - 融合向量与关键词检索.

    Args:
        session: 异步数据库会话
        alpha: 向量权重 (0-1), 默认 0.7
        bm25_limit: BM25 检索数量上限, 默认 20
    """

    def __init__(
        self,
        session: AsyncSession,
        alpha: float = 0.7,
        bm25_limit: int = 20,
    ) -> None:
        self.session = session
        self.alpha = alpha
        self.bm25_limit = bm25_limit
        self.matcher = ExperienceMatcher(session)

    async def search(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.0,
        domain: str | None = None,
        task_type: str | None = None,
        user_id: str | None = None,
        visibility_levels: list[str] | None = None,
        exclude_user_id: str | None = None,
        community_ids: list[str] | None = None,
    ) -> list[HybridSearchResult]:
        """执行混合检索.

        1. 向量检索获取 top-N 候选
        2. BM25 全文检索获取 top-N 候选
        3. 融合两路结果，加权计算最终分数
        4. 按 hybrid_score 降序返回
        """
        # 1. 向量检索
        vector_results = await self.matcher.match_by_vector(
            query=query,
            limit=limit * 2,  # 多取一些用于融合
            min_similarity=min_similarity,
            domain=domain,
            task_type=task_type,
            user_id=user_id,
            visibility_levels=visibility_levels,
            exclude_user_id=exclude_user_id,
            community_ids=community_ids,
        )

        # 2. BM25 全文检索
        keyword_results = await self._bm25_search(
            query=query,
            limit=self.bm25_limit,
            domain=domain,
            task_type=task_type,
            user_id=user_id,
            visibility_levels=visibility_levels,
            exclude_user_id=exclude_user_id,
            community_ids=community_ids,
        )

        # 3. 融合结果
        # 收集所有候选 ID
        vector_map: dict[str, tuple[float, object]] = {}
        for r in vector_results:
            vector_map[str(r.experience.id)] = (r.similarity, r.experience)

        keyword_map: dict[str, float] = {}
        for r in keyword_results:
            keyword_map[r["id"]] = r["score"]

        all_ids = set(vector_map.keys()) | set(keyword_map.keys())

        # 归一化 BM25 分数
        max_bm25 = max(keyword_map.values()) if keyword_map else 1.0

        # 4. 计算混合分数
        results: list[HybridSearchResult] = []
        for eid in all_ids:
            vec_score, exp = vector_map.get(eid, (0.0, None))
            kw_score = keyword_map.get(eid, 0.0)
            kw_score_norm = kw_score / max_bm25 if max_bm25 > 0 else 0.0

            hybrid = self.alpha * vec_score + (1 - self.alpha) * kw_score_norm

            # 如果向量检索没有这条经验，从 BM25 结果获取
            if exp is None:
                exp = await self._fetch_experience(eid)
                if exp is None:
                    continue

            results.append(HybridSearchResult(
                experience_id=eid,
                vector_score=vec_score,
                keyword_score=kw_score_norm,
                hybrid_score=hybrid,
                experience=exp,
            ))

        # 按 hybrid_score 降序排序
        results.sort(key=lambda r: r.hybrid_score, reverse=True)
        return results[:limit]

    async def _bm25_search(
        self,
        query: str,
        limit: int = 20,
        domain: str | None = None,
        task_type: str | None = None,
        user_id: str | None = None,
        visibility_levels: list[str] | None = None,
        exclude_user_id: str | None = None,
        community_ids: list[str] | None = None,
    ) -> list[dict]:
        """使用 PostgreSQL ts_rank 进行全文检索.

        在 intent 列上构建 tsvector，使用 plainto_tsquery 匹配。
        """
        # 构建查询条件
        conditions = ["evaluation_status != 'pending'"]
        params: dict = {"query_text": query, "limit_val": limit}

        if domain:
            conditions.append("context->>'domain' = :domain")
            params["domain"] = domain
        if task_type:
            conditions.append("context->>'task_type' = :task_type")
            params["task_type"] = task_type
        if user_id:
            conditions.append("user_id = :user_id")
            params["user_id"] = user_id
        if visibility_levels:
            conditions.append("visibility = ANY(:visibility_levels)")
            params["visibility_levels"] = visibility_levels
        if exclude_user_id:
            conditions.append("(user_id IS NULL OR user_id != :exclude_user_id)")
            params["exclude_user_id"] = exclude_user_id
        if community_ids:
            conditions.append("(visibility != 'community' OR community_id = ANY(:community_ids))")
            params["community_ids"] = community_ids

        sql = text("""
            SELECT id,
                   ts_rank(
                       to_tsvector('simple', coalesce(intent, '') || ' ' || coalesce(context->>'domain', '')),
                       plainto_tsquery('simple', :query_text)
                   ) as score
            FROM experiences
            WHERE """ + " AND ".join(conditions) + """
              AND to_tsvector('simple', coalesce(intent, '') || ' ' || coalesce(context->>'domain', ''))
                  @@ plainto_tsquery('simple', :query_text)
            ORDER BY score DESC
            LIMIT :limit_val
        """)

        result = await self.session.execute(sql, params)
        return [{"id": str(row[0]), "score": float(row[1])} for row in result.fetchall()]

    async def _fetch_experience(self, exp_id: str):
        """根据 ID 获取 Experience 对象."""
        from app.models.experience import Experience
        from sqlalchemy import select

        # 用 ORM 方式获取
        result = await self.session.execute(
            select(Experience).where(Experience.id == exp_id)
        )
        return result.scalar_one_or_none()
