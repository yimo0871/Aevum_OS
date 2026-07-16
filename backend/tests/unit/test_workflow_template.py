"""Unit tests for WorkflowTemplate model, schemas, and repository."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.models.workflow_template import WorkflowTemplate
from app.schemas.workflow_template import (
    WorkflowTemplateCreate,
    WorkflowTemplateListResponse,
    WorkflowTemplateResponse,
    WorkflowTemplateUpdate,
)
from app.services.experience.workflow_repository import WorkflowTemplateRepository


# ── Helper factories ──


def _make_template_create(**overrides) -> WorkflowTemplateCreate:
    """Build a WorkflowTemplateCreate schema for testing."""
    defaults = dict(
        name="Docker 部署 Python 应用",
        description="使用 Docker 容器化部署",
        domain="devops",
        task_type="deployment",
        steps=[{"name": "build", "action": "docker build"}],
        tools=["docker", "kubectl"],
        expected_outcome={"success_criteria": "服务运行正常"},
        visibility="public",
    )
    defaults.update(overrides)
    return WorkflowTemplateCreate(**defaults)


def _make_template(**overrides) -> WorkflowTemplate:
    """Build a WorkflowTemplate ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        name="测试模板",
        description="测试描述",
        domain="devops",
        task_type="deployment",
        steps=[{"name": "step1"}],
        tools=["docker"],
        expected_outcome={"success": True},
        success_rate=0.85,
        usage_count=10,
        visibility="public",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return WorkflowTemplate(**defaults)


# ── Model tests ──


class TestWorkflowTemplateModel:
    """Test WorkflowTemplate ORM model."""

    def test_creation(self) -> None:
        template = WorkflowTemplate(
            name="测试模板",
            description="描述",
            domain="devops",
            task_type="deployment",
        )
        assert template.name == "测试模板"
        assert template.domain == "devops"
        assert template.task_type == "deployment"

    def test_defaults(self) -> None:
        template = WorkflowTemplate(name="T", domain="d", task_type="t")
        # Before flush, Python-side defaults may not be set yet (server_default)
        assert template.name == "T"
        assert template.domain == "d"
        assert template.task_type == "t"

    def test_repr(self) -> None:
        template = WorkflowTemplate(name="我的模板", domain="d", task_type="t")
        repr_str = repr(template)
        assert "WorkflowTemplate" in repr_str

    def test_to_dict(self) -> None:
        template = _make_template()
        d = template.to_dict()
        assert d["name"] == "测试模板"
        assert d["domain"] == "devops"
        assert d["steps"] == [{"name": "step1"}]
        assert d["tools"] == ["docker"]
        assert d["success_rate"] == 0.85
        assert d["usage_count"] == 10
        assert d["id"] == str(template.id)
        assert "created_at" in d


# ── Schema tests ──


class TestWorkflowTemplateSchemas:
    """Test Pydantic schemas."""

    def test_create_valid(self) -> None:
        data = _make_template_create()
        assert data.name == "Docker 部署 Python 应用"
        assert data.visibility == "public"
        assert data.steps == [{"name": "build", "action": "docker build"}]

    def test_create_invalid_visibility(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowTemplateCreate(
                name="T", domain="d", task_type="t", visibility="invalid"
            )

    def test_create_empty_name(self) -> None:
        with pytest.raises(ValidationError):
            WorkflowTemplateCreate(name="  ", domain="d", task_type="t")

    def test_update_partial(self) -> None:
        data = WorkflowTemplateUpdate(name="新名称")
        assert data.name == "新名称"
        assert data.description is None
        assert data.domain is None

    def test_response_from_attributes(self) -> None:
        template = _make_template()
        response = WorkflowTemplateResponse.model_validate(template)
        assert response.name == "测试模板"
        assert response.domain == "devops"
        assert response.success_rate == 0.85
        assert response.usage_count == 10

    def test_list_response(self) -> None:
        template = _make_template()
        resp = WorkflowTemplateListResponse(
            items=[WorkflowTemplateResponse.model_validate(template)],
            total=1,
            page=1,
            page_size=20,
        )
        assert resp.total == 1
        assert len(resp.items) == 1
        assert resp.page == 1


# ── Repository tests ──


class TestWorkflowTemplateRepositoryCreate:
    """Test create operation."""

    @pytest.mark.asyncio
    async def test_create_success(self) -> None:
        session = AsyncMock()
        repo = WorkflowTemplateRepository(session)
        data = _make_template_create()

        result = await repo.create(data)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_maps_all_fields(self) -> None:
        session = AsyncMock()
        repo = WorkflowTemplateRepository(session)
        data = _make_template_create()

        await repo.create(data)

        added_obj = session.add.call_args[0][0]
        assert added_obj.name == "Docker 部署 Python 应用"
        assert added_obj.domain == "devops"
        assert added_obj.task_type == "deployment"
        assert added_obj.steps == [{"name": "build", "action": "docker build"}]
        assert added_obj.tools == ["docker", "kubectl"]
        assert added_obj.expected_outcome == {"success_criteria": "服务运行正常"}
        assert added_obj.visibility == "public"


class TestWorkflowTemplateRepositoryGetById:
    """Test get_by_id operation."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self) -> None:
        session = AsyncMock()
        template = _make_template()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        result = await repo.get_by_id(template.id)

        assert result is template
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestWorkflowTemplateRepositoryList:
    """Test list operation with pagination and filters."""

    @pytest.mark.asyncio
    async def test_list_basic(self) -> None:
        session = AsyncMock()
        template_list = [_make_template(), _make_template()]

        count_result = MagicMock()
        count_result.scalar.return_value = 2
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = template_list
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = WorkflowTemplateRepository(session)
        templates, total = await repo.list(page=1, page_size=20)

        assert total == 2
        assert len(templates) == 2
        assert templates == template_list

    @pytest.mark.asyncio
    async def test_list_with_filters(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [_make_template()]
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = WorkflowTemplateRepository(session)
        templates, total = await repo.list(
            page=1, page_size=10, domain="devops", task_type="deployment"
        )

        assert total == 1
        assert len(templates) == 1
        assert session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_list_empty(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = WorkflowTemplateRepository(session)
        templates, total = await repo.list()

        assert total == 0
        assert templates == []

    @pytest.mark.asyncio
    async def test_list_count_none_returns_zero(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = None
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = WorkflowTemplateRepository(session)
        _, total = await repo.list()

        assert total == 0

    @pytest.mark.asyncio
    async def test_list_pagination_offset(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 50
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [_make_template()]
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = WorkflowTemplateRepository(session)
        _, total = await repo.list(page=3, page_size=10)

        assert total == 50


class TestWorkflowTemplateRepositoryUpdate:
    """Test update operation."""

    @pytest.mark.asyncio
    async def test_update_success(self) -> None:
        session = AsyncMock()
        template = _make_template()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        update_data = WorkflowTemplateUpdate(
            name="更新后的名称",
            description="新描述",
            steps=[{"name": "new_step"}],
        )
        result = await repo.update(template.id, update_data)

        assert result is template
        assert template.name == "更新后的名称"
        assert template.description == "新描述"
        assert template.steps == [{"name": "new_step"}]
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        update_data = WorkflowTemplateUpdate(name="新名称")
        result = await repo.update(uuid.uuid4(), update_data)

        assert result is None


class TestWorkflowTemplateRepositoryIncrementUsage:
    """Test increment_usage operation."""

    @pytest.mark.asyncio
    async def test_increment_usage_success(self) -> None:
        session = AsyncMock()
        template = _make_template(usage_count=5)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        await repo.increment_usage(template.id)

        assert template.usage_count == 6
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_increment_usage_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        await repo.increment_usage(uuid.uuid4())

        # Should not raise, just silently skip
        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_increment_usage_from_zero(self) -> None:
        session = AsyncMock()
        template = _make_template(usage_count=0)
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = template
        session.execute.return_value = result_mock

        repo = WorkflowTemplateRepository(session)
        await repo.increment_usage(template.id)

        assert template.usage_count == 1
