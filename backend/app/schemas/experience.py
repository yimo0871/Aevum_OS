"""Pydantic schemas for Experience objects - API contracts."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ── 嵌套结构 ──


class ExperienceContext(BaseModel):
    """经验上下文."""

    domain: str = Field(..., description="领域（如 devops, frontend, data）")
    task_type: str = Field(..., description="任务类型（如 deployment, testing, analysis）")
    constraints: dict = Field(default_factory=dict, description="约束条件")


class ExperienceExecution(BaseModel):
    """执行过程."""

    steps: list[dict] = Field(default_factory=list, description="执行步骤")
    tools: list[str] = Field(default_factory=list, description="使用的工具")
    trace: dict = Field(default_factory=dict, description="完整追踪信息")


class ExperienceOutcome(BaseModel):
    """执行结果."""

    success: bool = Field(..., description="是否成功")
    metrics: dict = Field(default_factory=dict, description="指标数据")


class ExperienceReflection(BaseModel):
    """反思."""

    what_worked: list[str] = Field(default_factory=list, description="什么有效")
    what_failed: list[str] = Field(default_factory=list, description="什么失败")
    why: str = Field(default="", description="原因分析")


class ExperienceProvenance(BaseModel):
    """来源追溯."""

    human_signals: list[dict] = Field(default_factory=list, description="人类信号")
    agent_signals: list[dict] = Field(default_factory=list, description="Agent 信号")
    external_sources: list[dict] = Field(default_factory=list, description="外部来源")


# ── API 请求/响应模型 ──


class ExperienceBase(BaseModel):
    """Experience 基础字段（创建和更新共用）."""

    context: ExperienceContext
    intent: str = Field(..., min_length=1, max_length=2000, description="意图")
    execution: ExperienceExecution = Field(default_factory=ExperienceExecution)
    outcome: ExperienceOutcome
    reflection: ExperienceReflection = Field(default_factory=ExperienceReflection)
    reusable_patterns: list[dict] = Field(default_factory=list, description="可复用模式")
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0, description="置信度评分")
    provenance: ExperienceProvenance = Field(default_factory=ExperienceProvenance)
    version: int = Field(default=1, ge=1, description="版本号")
    visibility: str = Field(
        default="private",
        pattern="^(private|community|public)$",
        description="可见性: private(仅创建者) | community(同社区) | public(所有人)",
    )
    community_id: UUID | None = Field(None, description="所属社区 ID")

    @field_validator("intent")
    @classmethod
    def intent_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("intent must not be empty")
        return v.strip()


class ExperienceCreate(ExperienceBase):
    """创建 Experience 请求."""

    user_id: UUID | None = Field(None, description="关联用户 ID（数据隔离）")


class ExperienceUpdate(BaseModel):
    """更新 Experience 请求（所有字段可选）."""

    context: ExperienceContext | None = None
    intent: str | None = Field(None, min_length=1, max_length=2000)
    execution: ExperienceExecution | None = None
    outcome: ExperienceOutcome | None = None
    reflection: ExperienceReflection | None = None
    reusable_patterns: list[dict] | None = None
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    provenance: ExperienceProvenance | None = None
    version: int | None = Field(None, ge=1)
    evaluation_status: str | None = Field(None, pattern="^(pending|evaluated|skipped)$")
    visibility: str | None = Field(None, pattern="^(private|community|public)$")
    community_id: UUID | None = Field(None, description="所属社区 ID")


class ExperienceResponse(ExperienceBase):
    """Experience 响应."""

    id: UUID
    timestamp: datetime
    user_id: UUID | None = Field(None, description="关联用户 ID（数据隔离）")
    visibility: str = "private"
    community_id: UUID | None = Field(None, description="所属社区 ID")
    evaluation_status: str = "pending"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExperienceWithRelations(ExperienceResponse):
    """含关系的完整 Experience 响应."""

    relations: list[dict] = Field(default_factory=list, description="图谱关系")

    model_config = {"from_attributes": True}


class ExperienceListResponse(BaseModel):
    """经验列表响应（分页）."""

    items: list[ExperienceResponse]
    total: int
    page: int
    page_size: int


# ── 图谱关系 Schema ──


class RelationCreate(BaseModel):
    """创建经验关系."""

    target_id: UUID = Field(..., description="目标经验 ID")
    relation_type: str = Field(
        ..., pattern="^(reuse|citation|fork|improvement|dependency)$", description="关系类型"
    )
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="权重")
    metadata: dict = Field(default_factory=dict, description="元数据")


class RelationResponse(BaseModel):
    """经验关系响应."""

    id: UUID
    source_id: UUID
    target_id: UUID
    relation_type: str
    weight: float
    metadata: dict = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


# ── 检索 Schema ──


class ExperienceSearchRequest(BaseModel):
    """经验搜索请求."""

    query: str = Field(..., min_length=1, description="搜索查询")
    domain: str | None = Field(None, description="领域过滤")
    task_type: str | None = Field(None, description="任务类型过滤")
    min_confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="最低置信度")
    limit: int = Field(default=10, ge=1, le=100, description="返回数量")
    offset: int = Field(default=0, ge=0, description="偏移量")


class ExperienceSearchResult(BaseModel):
    """经验搜索结果（含匹配分数）."""

    experience: ExperienceResponse
    score: float = Field(..., description="匹配分数")
    matched_factors: dict = Field(default_factory=dict, description="匹配因子详情")
