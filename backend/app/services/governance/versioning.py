"""经验版本控制 - fork/improve/cite 操作."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience, ExperienceRelation


class VersionManager:
    """经验版本管理."""

    async def fork(self, source_experience_id, user_id, session: AsyncSession):
        """分叉经验 -- 创建副本并关联到原始经验."""
        # 1. 获取原始经验
        source = await session.get(Experience, source_experience_id)
        if source is None:
            return None

        # 2. 创建副本（version + 1, provenance 标记 fork 来源）
        new_provenance = dict(source.provenance) if source.provenance else {}
        new_provenance["forked_from"] = str(source.id)

        new_experience = Experience(
            context=source.context,
            intent=source.intent,
            execution=source.execution,
            outcome=source.outcome,
            reflection=source.reflection,
            reusable_patterns=source.reusable_patterns,
            confidence_score=source.confidence_score,
            provenance=new_provenance,
            version=(source.version or 1) + 1,
            user_id=user_id,
        )
        session.add(new_experience)
        await session.flush()
        await session.refresh(new_experience)

        # 3. 添加 fork 关系 (source -> new)
        relation = ExperienceRelation(
            source_id=source.id,
            target_id=new_experience.id,
            relation_type="fork",
            weight=1.0,
            metadata_={"forked_from": str(source.id)},
        )
        session.add(relation)
        await session.flush()

        return new_experience

    async def improve(self, source_experience_id, improvements, user_id, session: AsyncSession):
        """改进经验 -- 基于原始经验创建改进版本."""
        # 1. 获取原始经验
        source = await session.get(Experience, source_experience_id)
        if source is None:
            return None

        # 2. 合并改进内容
        new_context = dict(source.context) if source.context else {}
        new_outcome = dict(source.outcome) if source.outcome else {}
        new_reflection = dict(source.reflection) if source.reflection else {}
        new_provenance = dict(source.provenance) if source.provenance else {}
        new_provenance["improved_from"] = str(source.id)

        intent = source.intent
        confidence_score = source.confidence_score

        if isinstance(improvements, dict):
            if "context" in improvements and isinstance(improvements["context"], dict):
                new_context.update(improvements["context"])
            if "outcome" in improvements and isinstance(improvements["outcome"], dict):
                new_outcome.update(improvements["outcome"])
            if "reflection" in improvements and isinstance(improvements["reflection"], dict):
                new_reflection.update(improvements["reflection"])
            if "intent" in improvements:
                intent = improvements["intent"]
            if "confidence_score" in improvements:
                confidence_score = improvements["confidence_score"]

        # 3. 创建新版本
        new_experience = Experience(
            context=new_context,
            intent=intent,
            execution=source.execution,
            outcome=new_outcome,
            reflection=new_reflection,
            reusable_patterns=source.reusable_patterns,
            confidence_score=confidence_score,
            provenance=new_provenance,
            version=(source.version or 1) + 1,
            user_id=user_id,
        )
        session.add(new_experience)
        await session.flush()
        await session.refresh(new_experience)

        # 4. 添加 improvement 关系 (source -> new)
        relation = ExperienceRelation(
            source_id=source.id,
            target_id=new_experience.id,
            relation_type="improvement",
            weight=0.8,
            metadata_={"improved_from": str(source.id)},
        )
        session.add(relation)
        await session.flush()

        return new_experience

    async def cite(self, source_experience_id, citing_experience_id, session: AsyncSession):
        """引用经验 -- 添加 citation 关系.

        source_experience_id: 被引用的经验 ID（target）
        citing_experience_id: 引用方经验 ID（source）
        """
        relation = ExperienceRelation(
            source_id=citing_experience_id,
            target_id=source_experience_id,
            relation_type="citation",
            weight=1.0,
            metadata_={},
        )
        session.add(relation)
        await session.flush()
        await session.refresh(relation)
        return relation
