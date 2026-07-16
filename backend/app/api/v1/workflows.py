"""WorkflowTemplate CRUD API routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session
from app.models.user import User
from app.schemas.workflow_template import (
    WorkflowTemplateCreate,
    WorkflowTemplateListResponse,
    WorkflowTemplateResponse,
    WorkflowTemplateUpdate,
)
from app.services.experience.workflow_repository import WorkflowTemplateRepository

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/workflows",
    response_model=WorkflowTemplateListResponse,
    summary="列出工作流模板",
    description="分页列出工作流模板，支持按领域和任务类型过滤。",
)
async def list_workflows(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    domain: str | None = Query(None, description="领域过滤"),
    task_type: str | None = Query(None, description="任务类型过滤"),
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowTemplateListResponse:
    repo = WorkflowTemplateRepository(session)
    templates, total = await repo.list(
        page=page,
        page_size=page_size,
        domain=domain,
        task_type=task_type,
    )
    return WorkflowTemplateListResponse(
        items=[WorkflowTemplateResponse.model_validate(t) for t in templates],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/workflows/{workflow_id}",
    response_model=WorkflowTemplateResponse,
    summary="获取工作流模板",
    description="根据 ID 获取单个工作流模板。",
)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowTemplateResponse:
    repo = WorkflowTemplateRepository(session)
    template = await repo.get_by_id(workflow_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowTemplate {workflow_id} not found",
        )
    return WorkflowTemplateResponse.model_validate(template)


@router.post(
    "/workflows",
    response_model=WorkflowTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建工作流模板",
    description="创建一个新的工作流模板。",
)
async def create_workflow(
    data: WorkflowTemplateCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowTemplateResponse:
    repo = WorkflowTemplateRepository(session)
    template = await repo.create(data)
    return WorkflowTemplateResponse.model_validate(template)


@router.put(
    "/workflows/{workflow_id}",
    response_model=WorkflowTemplateResponse,
    summary="更新工作流模板",
    description="更新一个工作流模板。",
)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowTemplateUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowTemplateResponse:
    repo = WorkflowTemplateRepository(session)
    template = await repo.update(workflow_id, data)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowTemplate {workflow_id} not found",
        )
    return WorkflowTemplateResponse.model_validate(template)


@router.post(
    "/workflows/{workflow_id}/use",
    response_model=WorkflowTemplateResponse,
    summary="记录模板使用",
    description="增加工作流模板的使用次数。",
)
async def use_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_db_session),
) -> WorkflowTemplateResponse:
    repo = WorkflowTemplateRepository(session)
    template = await repo.get_by_id(workflow_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"WorkflowTemplate {workflow_id} not found",
        )
    await repo.increment_usage(workflow_id)
    await session.refresh(template)
    return WorkflowTemplateResponse.model_validate(template)
