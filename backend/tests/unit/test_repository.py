"""Unit tests for ExperienceRepository - CRUD operations."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.experience import Experience
from app.schemas.experience import (
    ExperienceContext,
    ExperienceCreate,
    ExperienceExecution,
    ExperienceOutcome,
    ExperienceProvenance,
    ExperienceReflection,
    ExperienceUpdate,
)
from app.services.experience.repository import ExperienceRepository


def _make_experience_create(**overrides) -> ExperienceCreate:
    """Build an ExperienceCreate schema for testing."""
    defaults = dict(
        context=ExperienceContext(domain="devops", task_type="deployment", constraints={"env": "prod"}),
        intent="Deploy FastAPI to production",
        execution=ExperienceExecution(steps=[{"action": "build"}], tools=["docker"], trace={}),
        outcome=ExperienceOutcome(success=True, metrics={"time": 45}),
        reflection=ExperienceReflection(what_worked=["docker"], what_failed=[], why="ok"),
        reusable_patterns=[{"pattern": "multi-stage"}],
        confidence_score=0.9,
        provenance=ExperienceProvenance(agent_signals=[{"agent_id": "a1"}]),
        version=1,
    )
    defaults.update(overrides)
    return ExperienceCreate(**defaults)


def _make_experience(**overrides) -> Experience:
    """Build an Experience ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        timestamp=datetime.now(timezone.utc),
        context={"domain": "devops", "task_type": "deployment"},
        intent="Deploy app",
        execution={"steps": [], "tools": [], "trace": {}},
        outcome={"success": True, "metrics": {}},
        reflection={"what_worked": [], "what_failed": [], "why": ""},
        reusable_patterns=[],
        confidence_score=0.8,
        provenance={"agent_signals": []},
        version=1,
        evaluation_status="pending",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Experience(**defaults)


class TestExperienceRepositoryCreate:
    """Test create operation."""

    @pytest.mark.asyncio
    async def test_create_success(self) -> None:
        session = AsyncMock()

        repo = ExperienceRepository(session)
        data = _make_experience_create()

        result = await repo.create(data)

        # Verify session.add and flush were called
        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_create_maps_all_fields(self) -> None:
        session = AsyncMock()
        repo = ExperienceRepository(session)
        data = _make_experience_create()

        await repo.create(data)

        # Verify the object passed to session.add has correct fields
        added_obj = session.add.call_args[0][0]
        assert added_obj.intent == "Deploy FastAPI to production"
        assert added_obj.confidence_score == 0.9
        assert added_obj.version == 1
        assert added_obj.reusable_patterns == [{"pattern": "multi-stage"}]
        assert added_obj.context["domain"] == "devops"
        assert added_obj.outcome["success"] is True
        assert added_obj.reflection["what_worked"] == ["docker"]
        assert added_obj.provenance["agent_signals"] == [{"agent_id": "a1"}]


class TestExperienceRepositoryGetById:
    """Test get_by_id operation."""

    @pytest.mark.asyncio
    async def test_get_by_id_found(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        result = await repo.get_by_id(exp.id)

        assert result is exp
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        result = await repo.get_by_id(uuid.uuid4())

        assert result is None


class TestExperienceRepositoryList:
    """Test list operation with pagination and filters."""

    @pytest.mark.asyncio
    async def test_list_basic(self) -> None:
        session = AsyncMock()
        exp_list = [_make_experience(), _make_experience()]

        # First execute -> count, second execute -> data
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = exp_list
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = ExperienceRepository(session)
        experiences, total = await repo.list(page=1, page_size=20)

        assert total == 2
        assert len(experiences) == 2
        assert experiences == exp_list

    @pytest.mark.asyncio
    async def test_list_with_filters(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 1
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [_make_experience()]
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = ExperienceRepository(session)
        experiences, total = await repo.list(
            page=1,
            page_size=10,
            domain="devops",
            task_type="deployment",
            min_confidence=0.5,
            evaluation_status="evaluated",
        )

        assert total == 1
        assert len(experiences) == 1
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

        repo = ExperienceRepository(session)
        experiences, total = await repo.list()

        assert total == 0
        assert experiences == []

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

        repo = ExperienceRepository(session)
        _, total = await repo.list()

        assert total == 0

    @pytest.mark.asyncio
    async def test_list_pagination_offset(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 50
        data_result = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [_make_experience()]
        data_result.scalars.return_value = scalars_mock

        session.execute.side_effect = [count_result, data_result]

        repo = ExperienceRepository(session)
        experiences, total = await repo.list(page=3, page_size=10)

        assert total == 50


class TestExperienceRepositoryUpdate:
    """Test update operation."""

    @pytest.mark.asyncio
    async def test_update_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(intent="Updated intent")
        result = await repo.update(uuid.uuid4(), update_data)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_simple_fields(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(
            intent="Updated intent",
            confidence_score=0.95,
            version=2,
            evaluation_status="evaluated",
            reusable_patterns=[{"pattern": "new"}],
        )
        result = await repo.update(exp.id, update_data)

        assert result is exp
        assert exp.intent == "Updated intent"
        assert exp.confidence_score == 0.95
        assert exp.version == 2
        assert exp.evaluation_status == "evaluated"
        assert exp.reusable_patterns == [{"pattern": "new"}]
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_nested_context(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(
            context=ExperienceContext(domain="frontend", task_type="testing"),
        )
        result = await repo.update(exp.id, update_data)

        assert result is exp
        assert exp.context["domain"] == "frontend"
        assert exp.context["task_type"] == "testing"

    @pytest.mark.asyncio
    async def test_update_nested_outcome(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(
            outcome=ExperienceOutcome(success=False, metrics={"error": 1}),
        )
        result = await repo.update(exp.id, update_data)

        assert result is exp
        assert exp.outcome["success"] is False

    @pytest.mark.asyncio
    async def test_update_nested_reflection(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(
            reflection=ExperienceReflection(what_worked=["x"], what_failed=["y"], why="z"),
        )
        result = await repo.update(exp.id, update_data)

        assert result is exp
        assert exp.reflection["what_worked"] == ["x"]

    @pytest.mark.asyncio
    async def test_update_nested_provenance(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(
            provenance=ExperienceProvenance(human_signals=[{"type": "review"}]),
        )
        result = await repo.update(exp.id, update_data)

        assert result is exp
        assert exp.provenance["human_signals"] == [{"type": "review"}]

    @pytest.mark.asyncio
    async def test_update_nested_execution(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        update_data = ExperienceUpdate(
            execution=ExperienceExecution(steps=[{"a": 1}], tools=["t"], trace={"k": "v"}),
        )
        result = await repo.update(exp.id, update_data)

        assert result is exp
        assert exp.execution["steps"] == [{"a": 1}]


class TestExperienceRepositoryDelete:
    """Test delete operation."""

    @pytest.mark.asyncio
    async def test_delete_success(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = exp
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        result = await repo.delete(exp.id)

        assert result is True
        session.delete.assert_awaited_once_with(exp)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        repo = ExperienceRepository(session)
        result = await repo.delete(uuid.uuid4())

        assert result is False
        session.delete.assert_not_awaited()


class TestExperienceRepositoryUpdateEmbedding:
    """Test update_embedding operation."""

    @pytest.mark.asyncio
    async def test_update_embedding(self) -> None:
        session = AsyncMock()
        repo = ExperienceRepository(session)
        exp_id = uuid.uuid4()
        embedding = [0.1, 0.2, 0.3]

        await repo.update_embedding(exp_id, embedding)

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()
