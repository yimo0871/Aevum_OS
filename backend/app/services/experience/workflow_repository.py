"""WorkflowTemplate repository - CRUD operations for WorkflowTemplate objects."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_template import WorkflowTemplate
from app.schemas.workflow_template import WorkflowTemplateCreate, WorkflowTemplateUpdate


class WorkflowTemplateRepository:
    """工作流模板存储服务 - WorkflowTemplate 对象的 CRUD 操作."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: WorkflowTemplateCreate) -> WorkflowTemplate:
        """创建工作流模板."""
        template = WorkflowTemplate(
            name=data.name,
            description=data.description,
            domain=data.domain,
            task_type=data.task_type,
            steps=data.steps,
            tools=data.tools,
            expected_outcome=data.expected_outcome,
            visibility=data.visibility,
        )
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def get_by_id(self, template_id: UUID) -> WorkflowTemplate | None:
        """根据 ID 获取工作流模板."""
        result = await self.session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.id == template_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        page: int = 1,
        page_size: int = 20,
        domain: str | None = None,
        task_type: str | None = None,
    ) -> tuple[list[WorkflowTemplate], int]:
        """列出工作流模板（分页 + 过滤）.

        Returns:
            (templates, total_count)
        """
        query = select(WorkflowTemplate)

        # ── 过滤条件 ──
        if domain:
            query = query.where(WorkflowTemplate.domain == domain)
        if task_type:
            query = query.where(WorkflowTemplate.task_type == task_type)

        # ── 总数 ──
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar() or 0

        # ── 分页 ──
        offset = (page - 1) * page_size
        query = query.order_by(WorkflowTemplate.created_at.desc()).offset(offset).limit(page_size)
        result = await self.session.execute(query)
        templates = list(result.scalars().all())

        return templates, total

    async def update(
        self, template_id: UUID, data: WorkflowTemplateUpdate
    ) -> WorkflowTemplate | None:
        """更新工作流模板."""
        template = await self.get_by_id(template_id)
        if template is None:
            return None

        update_data = data.model_dump(exclude_unset=True)

        for field in [
            "name",
            "description",
            "domain",
            "task_type",
            "steps",
            "tools",
            "expected_outcome",
            "visibility",
        ]:
            if field in update_data and update_data[field] is not None:
                setattr(template, field, update_data[field])

        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def increment_usage(self, template_id: UUID) -> None:
        """增加模板使用次数."""
        template = await self.get_by_id(template_id)
        if template is not None:
            template.usage_count = (template.usage_count or 0) + 1
            await self.session.flush()
