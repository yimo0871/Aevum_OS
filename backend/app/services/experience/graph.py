"""Experience graph - 图谱关系管理."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import ExperienceRelation
from app.schemas.experience import RelationCreate


class ExperienceGraph:
    """经验图谱关系管理 - 添加/查询/删除经验之间的关系边.

    边类型:
    - reuse: 复用
    - citation: 引用
    - fork: 分叉
    - improvement: 改进
    - dependency: 依赖
    """

    VALID_RELATION_TYPES = {"reuse", "citation", "fork", "improvement", "dependency"}

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_relation(
        self, source_id: UUID, data: RelationCreate
    ) -> ExperienceRelation:
        """添加经验关系."""
        relation = ExperienceRelation(
            source_id=source_id,
            target_id=data.target_id,
            relation_type=data.relation_type,
            weight=data.weight,
            metadata_=data.metadata,
        )
        self.session.add(relation)
        await self.session.flush()
        await self.session.refresh(relation)
        return relation

    async def get_relations(
        self,
        experience_id: UUID,
        direction: str = "both",
        relation_type: str | None = None,
    ) -> list[ExperienceRelation]:
        """查询经验的关系.

        Args:
            experience_id: 经验 ID
            direction: "outgoing" (作为 source), "incoming" (作为 target), "both"
            relation_type: 可选的关系类型过滤
        """
        results: list[ExperienceRelation] = []

        if direction in ("outgoing", "both"):
            query = select(ExperienceRelation).where(
                ExperienceRelation.source_id == experience_id
            )
            if relation_type:
                query = query.where(ExperienceRelation.relation_type == relation_type)
            res = await self.session.execute(query)
            results.extend(res.scalars().all())

        if direction in ("incoming", "both"):
            query = select(ExperienceRelation).where(
                ExperienceRelation.target_id == experience_id
            )
            if relation_type:
                query = query.where(ExperienceRelation.relation_type == relation_type)
            res = await self.session.execute(query)
            results.extend(res.scalars().all())

        return results

    async def remove_relation(self, relation_id: UUID) -> bool:
        """删除经验关系."""
        result = await self.session.execute(
            select(ExperienceRelation).where(ExperienceRelation.id == relation_id)
        )
        relation = result.scalar_one_or_none()
        if relation is None:
            return False
        await self.session.delete(relation)
        await self.session.flush()
        return True

    async def get_connected_experiences(
        self, experience_id: UUID, max_depth: int = 1
    ) -> list[dict]:
        """获取连通的经验（BFS 遍历）.

        Args:
            experience_id: 起始经验 ID
            max_depth: 最大遍历深度

        Returns:
            list of {experience_id, relation_type, direction, depth}
        """
        visited: set[UUID] = {experience_id}
        results: list[dict] = []
        current_level = [experience_id]

        for depth in range(1, max_depth + 1):
            next_level: list[UUID] = []
            for exp_id in current_level:
                relations = await self.get_relations(exp_id)
                for rel in relations:
                    neighbor_id = rel.target_id if rel.source_id == exp_id else rel.source_id
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        next_level.append(neighbor_id)
                        results.append({
                            "experience_id": str(neighbor_id),
                            "relation_type": rel.relation_type,
                            "direction": "outgoing" if rel.source_id == exp_id else "incoming",
                            "weight": rel.weight,
                            "depth": depth,
                        })
            current_level = next_level
            if not current_level:
                break

        return results
