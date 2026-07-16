"""Experience repository - CRUD operations for Experience objects."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience
from app.schemas.experience import ExperienceCreate, ExperienceUpdate


def build_visibility_filter(current_user_id: str | None):
    """构建可见性过滤条件.

    规则:
    - 匿名用户 (current_user_id=None): 仅可见 visibility='public' 的经验
    - 已认证用户: 可见自己的所有经验 + 他人的 community/public 经验

    Args:
        current_user_id: 当前用户 ID（None 表示匿名）

    Returns:
        SQLAlchemy 过滤条件
    """
    if current_user_id is None:
        return Experience.visibility == "public"
    return or_(
        Experience.user_id == current_user_id,
        Experience.visibility.in_(["community", "public"]),
    )


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
            user_id=data.user_id,
            visibility=data.visibility,
            community_id=data.community_id,
        )
        self.session.add(experience)
        await self.session.flush()
        await self.session.refresh(experience)
        return experience

    async def get_by_id(
        self,
        experience_id: UUID,
        current_user_id: str | None = None,
    ) -> Experience | None:
        """根据 ID 获取经验（受可见性权限约束）.

        Args:
            experience_id: 经验 ID
            current_user_id: 当前用户 ID（None 表示匿名，仅可获取 public 经验）
        """
        query = select(Experience).where(Experience.id == experience_id)
        query = query.where(build_visibility_filter(current_user_id))
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def _get_by_id_unfiltered(self, experience_id: UUID) -> Experience | None:
        """根据 ID 获取经验（不过滤可见性，供内部操作使用）."""
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
        visibility: str | None = None,
        current_user_id: str | None = None,
    ) -> tuple[list[Experience], int]:
        """列出经验（分页 + 过滤）.

        Args:
            visibility: 显式按可见性过滤（private/community/public）
            current_user_id: 当前用户 ID，用于可见性权限过滤

        Returns:
            (experiences, total_count)
        """
        query = select(Experience)

        # ── 可见性权限过滤 ──
        if visibility:
            # 显式指定 visibility 时，仍需确保权限：私有经验仅创建者可见
            if visibility == "private" and current_user_id:
                query = query.where(
                    Experience.visibility == "private",
                    Experience.user_id == current_user_id,
                )
            elif visibility == "private":
                # 匿名用户无法看到任何私有经验
                query = query.where("1 = 0")
            else:
                query = query.where(Experience.visibility == visibility)
        else:
            query = query.where(build_visibility_filter(current_user_id))

        # ── 其他过滤条件 ──
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
        experience = await self._get_by_id_unfiltered(experience_id)
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
        for field in ["intent", "reusable_patterns", "confidence_score", "version", "evaluation_status", "visibility", "community_id"]:
            if field in update_data and update_data[field] is not None:
                setattr(experience, field, update_data[field])

        await self.session.flush()
        await self.session.refresh(experience)
        return experience

    async def delete(self, experience_id: UUID) -> bool:
        """删除经验."""
        experience = await self._get_by_id_unfiltered(experience_id)
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
