"""Experience repository - CRUD operations for Experience objects."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience
from app.schemas.experience import ExperienceCreate, ExperienceUpdate


class ExperienceRepository:
    """经验存储服务 - Experience 对象的 CRUD 操作."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: ExperienceCreate) -> Experience:
        """创建经验."""
        experience = Experience(
            context=data.context.model_dump(),
            intent=data.intent,
            execution=data.execution.model_dump(),
            outcome=data.outcome.model_dump(),
            reflection=data.reflection.model_dump(),
            reusable_patterns=data.reusable_patterns,
            confidence_score=data.confidence_score,
            provenance=data.provenance.model_dump(),
            version=data.version,
        )
        self.session.add(experience)
        await self.session.flush()
        await self.session.refresh(experience)
        return experience

    async def get_by_id(self, experience_id: UUID) -> Experience | None:
        """根据 ID 获取经验."""
        result = await self.session.execute(
            select(Experience).where(Experience.id == experience_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        domain: str | None = None,
        task_type: str | None = None,
        min_confidence: float | None = None,
        evaluation_status: str | None = None,
    ) -> tuple[list[Experience], int]:
        """列出经验（分页 + 过滤）.

        Returns:
            (experiences, total_count)
        """
        query = select(Experience)

        # ── 过滤条件 ──
        if domain:
            query = query.where(
                Experience.context["domain"].astext == domain
            )
        if task_type:
            query = query.where(
                Experience.context["task_type"].astext == task_type
            )
        if min_confidence is not None:
            query = query.where(Experience.confidence_score >= min_confidence)
        if evaluation_status:
            query = query.where(Experience.evaluation_status == evaluation_status)

        # ── 总数 ──
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # ── 分页 ──
        offset = (page - 1) * page_size
        query = query.order_by(Experience.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(query)
        experiences = list(result.scalars().all())

        return experiences, total

    async def update(self, experience_id: UUID, data: ExperienceUpdate) -> Experience | None:
        """更新经验."""
        experience = await self.get_by_id(experience_id)
        if experience is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # ── 处理嵌套模型 ──
        if "context" in update_data and update_data["context"] is not None:
            experience.context = update_data["context"] if isinstance(update_data["context"], dict) else update_data["context"].model_dump() if hasattr(update_data["context"], "model_dump") else update_data["context"]
        if "execution" in update_data and update_data["execution"] is not None:
            experience.execution = update_data["execution"] if isinstance(update_data["execution"], dict) else update_data["execution"].model_dump() if hasattr(update_data["execution"], "model_dump") else update_data["execution"]
        if "outcome" in update_data and update_data["outcome"] is not None:
            experience.outcome = update_data["outcome"] if isinstance(update_data["outcome"], dict) else update_data["outcome"].model_dump() if hasattr(update_data["outcome"], "model_dump") else update_data["outcome"]
        if "reflection" in update_data and update_data["reflection"] is not None:
            experience.reflection = update_data["reflection"] if isinstance(update_data["reflection"], dict) else update_data["reflection"].model_dump() if hasattr(update_data["reflection"], "model_dump") else update_data["reflection"]
        if "provenance" in update_data and update_data["provenance"] is not None:
            experience.provenance = update_data["provenance"] if isinstance(update_data["provenance"], dict) else update_data["provenance"].model_dump() if hasattr(update_data["provenance"], "model_dump") else update_data["provenance"]

        # ── 处理简单字段 ──
        for field in ["intent", "reusable_patterns", "confidence_score", "version", "evaluation_status"]:
            if field in update_data and update_data[field] is not None:
                setattr(experience, field, update_data[field])

        await self.session.flush()
        await self.session.refresh(experience)
        return experience

    async def delete(self, experience_id: UUID) -> bool:
        """删除经验."""
        experience = await self.get_by_id(experience_id)
        if experience is None:
            return False
        await self.session.delete(experience)
        await self.session.flush()
        return True

    async def update_embedding(self, experience_id: UUID, embedding: list[float]) -> None:
        """更新经验的向量嵌入."""
        from pgvector.sqlalchemy import Vector

        await self.session.execute(
            Experience.__table__.update()
            .where(Experience.__table__.c.id == experience_id)
            .values(embedding=embedding)
        )
        await self.session.flush()
