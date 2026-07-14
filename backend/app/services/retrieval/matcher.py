"""Experience matcher - 经验相似度匹配.

使用向量余弦相似度计算经验与查询上下文的匹配度。
"""

import math
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience
from app.services.retrieval.embedder import get_embedder


@dataclass
class MatchResult:
    """匹配结果."""

    experience: Experience
    similarity: float
    matched_fields: list[str]

    def to_dict(self) -> dict:
        return {
            "experience_id": str(self.experience.id),
            "similarity": self.similarity,
            "matched_fields": self.matched_fields,
        }


class ExperienceMatcher:
    """经验匹配器 - 计算查询与经验的相似度.

    匹配方式:
    1. 向量相似度（pgvector 余弦距离）- 主要方式
    2. 关键词匹配 - 辅助方式
    3. 上下文匹配（领域、任务类型）- 过滤条件
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.embedder = get_embedder()

    async def match_by_vector(
        self,
        query: str,
        limit: int = 10,
        min_similarity: float = 0.0,
        domain: str | None = None,
        task_type: str | None = None,
    ) -> list[MatchResult]:
        """向量相似度匹配.

        Args:
            query: 搜索查询文本
            limit: 返回数量
            min_similarity: 最低相似度阈值
            domain: 领域过滤
            task_type: 任务类型过滤

        Returns:
            匹配结果列表（按相似度降序）
        """
        # 生成查询向量
        if hasattr(self.embedder, "embed_async"):
            query_vector = await self.embedder.embed_async(query)
        else:
            query_vector = await self.embedder.embed(query)

        # 将向量转为 pgvector 格式字符串
        vector_str = f"[{','.join(str(v) for v in query_vector)}]"

        # 使用 pgvector 的余弦距离查询
        sql = text("""
            SELECT id, timestamp, context, intent, execution, outcome,
                   reflection, reusable_patterns, confidence_score,
                   provenance, version, evaluation_status, created_at, updated_at,
                   1 - (embedding <=> :vector) as similarity
            FROM experiences
            WHERE evaluation_status != 'pending'
        """)

        params: dict = {"vector": vector_str}

        if domain:
            sql = text(sql.text + " AND context->>'domain' = :domain")
            params["domain"] = domain

        if task_type:
            sql = text(sql.text + " AND context->>'task_type' = :task_type")
            params["task_type"] = task_type

        sql = text(sql.text + " AND 1 - (embedding <=> :vector) >= :min_sim")
        params["min_sim"] = min_similarity

        sql = text(sql.text + " ORDER BY embedding <=> :vector LIMIT :limit")
        params["limit"] = limit

        result = await self.session.execute(sql, params)
        rows = result.fetchall()

        matches: list[MatchResult] = []
        for row in rows:
            # 重建 Experience 对象
            exp = Experience(
                id=row[0],
                timestamp=row[1],
                context=row[2],
                intent=row[3],
                execution=row[4],
                outcome=row[5],
                reflection=row[6],
                reusable_patterns=row[7],
                confidence_score=row[8],
                provenance=row[9],
                version=row[10],
                evaluation_status=row[11],
                created_at=row[12],
                updated_at=row[13],
            )
            similarity = row[14] if row[14] is not None else 0.0
            matches.append(MatchResult(
                experience=exp,
                similarity=similarity,
                matched_fields=["vector"],
            ))

        return matches

    async def match_by_keywords(
        self,
        query: str,
        limit: int = 10,
        domain: str | None = None,
    ) -> list[MatchResult]:
        """关键词匹配（当向量不可用时的降级方案）."""
        keywords = query.lower().split()

        query_stmt = select(Experience).where(
            Experience.evaluation_status != "pending"
        )

        if domain:
            query_stmt = query_stmt.where(
                Experience.context["domain"].astext == domain
            )

        result = await self.session.execute(query_stmt.limit(limit * 3))
        experiences = result.scalars().all()

        matches: list[MatchResult] = []
        for exp in experiences:
            # 计算关键词匹配度
            intent_lower = (exp.intent or "").lower()
            matched_count = sum(1 for kw in keywords if kw in intent_lower)
            if matched_count > 0:
                similarity = matched_count / len(keywords) if keywords else 0
                matches.append(MatchResult(
                    experience=exp,
                    similarity=similarity,
                    matched_fields=["intent"],
                ))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:limit]

    @staticmethod
    def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
        """计算两个向量的余弦相似度."""
        if len(vec_a) != len(vec_b) or len(vec_a) == 0:
            return 0.0

        dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)
