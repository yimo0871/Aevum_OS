"""Unit tests for CoCreationSession model, schemas, and workflow logic - 人机协同创作."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.v1.cocreation import (
    _create_session,
    _explore_session,
    _get_session,
    _judge_session,
)
from app.models.cocreation import CoCreationSession
from app.schemas.cocreation import (
    CoCreationJudgeRequest,
    CoCreationSessionCreate,
    CoCreationSessionResponse,
)
from app.services.retrieval.matcher import MatchResult


# ── Helpers ──


def _make_session(**overrides) -> CoCreationSession:
    """Build a CoCreationSession ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        task_description="Design a CI/CD pipeline",
        domain="devops",
        human_constraints={"max_budget": 1000, "language": "python"},
        agent_proposals=None,
        human_feedback=None,
        human_rating=None,
        status="defined",
        experience_id=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return CoCreationSession(**defaults)


def _make_match_result(intent="Deploy app", score=0.9) -> MatchResult:
    """Build a MatchResult for testing."""
    from app.models.experience import Experience

    exp = Experience(
        id=uuid.uuid4(),
        context={"domain": "devops"},
        intent=intent,
        execution={},
        outcome={"success": True},
        reflection={},
        reusable_patterns=[],
        confidence_score=0.8,
        provenance={},
        version=1,
    )
    return MatchResult(experience=exp, similarity=score, matched_fields=["intent"])


def _make_mock_session() -> AsyncMock:
    """Build a mock async session."""
    session = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    return session


# ── Model tests ──


class TestCoCreationSessionModel:
    """Test CoCreationSession ORM model."""

    def test_creation(self) -> None:
        s = _make_session(task_description="Build a web app", domain="frontend")
        assert s.task_description == "Build a web app"
        assert s.domain == "frontend"

    def test_defaults(self) -> None:
        s = CoCreationSession(
            user_id=uuid.uuid4(),
            task_description="Test task",
        )
        # Defaults are applied at flush/commit time, not at instantiation
        assert s.task_description == "Test task"
        assert s.user_id is not None

    def test_repr(self) -> None:
        s = _make_session(status="exploring")
        assert "exploring" in repr(s)

    def test_to_dict(self) -> None:
        s = _make_session(
            human_feedback="Good",
            human_rating=4,
            status="completed",
        )
        d = s.to_dict()
        assert d["status"] == "completed"
        assert d["human_feedback"] == "Good"
        assert d["human_rating"] == 4
        assert d["id"] == str(s.id)
        assert d["experience_id"] is None
        assert "created_at" in d

    def test_to_dict_with_proposals(self) -> None:
        proposals = [{"approach": "test"}]
        s = _make_session(agent_proposals=proposals)
        d = s.to_dict()
        assert d["agent_proposals"] == proposals


# ── Schema tests ──


class TestCoCreationSchemas:
    """Test Co-creation Pydantic schemas."""

    def test_session_create_valid(self) -> None:
        data = CoCreationSessionCreate(
            task_description="Build API",
            domain="backend",
        )
        assert data.task_description == "Build API"
        assert data.domain == "backend"
        assert data.human_constraints == {}

    def test_session_create_with_constraints(self) -> None:
        data = CoCreationSessionCreate(
            task_description="Deploy",
            human_constraints={"timeout": 300, "env": "prod"},
        )
        assert data.human_constraints["timeout"] == 300
        assert data.domain == "general"

    def test_judge_request_valid(self) -> None:
        data = CoCreationJudgeRequest(accepted=True, feedback="Great", rating=5)
        assert data.accepted is True
        assert data.rating == 5

    def test_judge_request_invalid_rating(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            CoCreationJudgeRequest(accepted=True, rating=6)

    def test_judge_request_default_rating(self) -> None:
        data = CoCreationJudgeRequest(accepted=False)
        assert data.rating == 3
        assert data.feedback == ""

    def test_session_response_from_attributes(self) -> None:
        s = _make_session()
        response = CoCreationSessionResponse.model_validate(s)
        assert response.task_description == "Design a CI/CD pipeline"
        assert response.status == "defined"


# ── _create_session tests ──


class TestCreateSession:
    """Test _create_session logic."""

    @pytest.mark.asyncio
    async def test_create_session_success(self) -> None:
        session = _make_mock_session()
        user_id = uuid.uuid4()
        data = CoCreationSessionCreate(
            task_description="Build something",
            domain="devops",
            human_constraints={"budget": 500},
        )

        result = await _create_session(user_id, data, session)

        session.add.assert_called_once()
        assert result.task_description == "Build something"
        assert result.status == "defined"
        assert result.user_id == user_id
        assert result.human_constraints == {"budget": 500}


# ── _get_session tests ──


class TestGetSession:
    """Test _get_session logic."""

    @pytest.mark.asyncio
    async def test_get_session_found(self) -> None:
        cocreation = _make_session()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = cocreation
        session.execute = AsyncMock(return_value=result_mock)

        result = await _get_session(cocreation.id, cocreation.user_id, session)

        assert result is cocreation

    @pytest.mark.asyncio
    async def test_get_session_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        result = await _get_session(uuid.uuid4(), uuid.uuid4(), session)

        assert result is None


# ── _explore_session tests ──


class TestExploreSession:
    """Test _explore_session logic."""

    @pytest.mark.asyncio
    async def test_explore_sets_status_and_proposals(self) -> None:
        cocreation = _make_session(status="defined")
        session = _make_mock_session()

        matches = [_make_match_result(intent="Deploy with Docker", score=0.9)]
        matcher = AsyncMock()
        matcher.match_by_keywords = AsyncMock(return_value=matches)

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.api.v1.cocreation.ExperienceMatcher",
                lambda s: matcher,
            )
            proposals = await _explore_session(cocreation, session)

        assert cocreation.status == "exploring"
        assert len(proposals) == 1
        assert proposals[0]["intent"] == "Deploy with Docker"
        assert cocreation.agent_proposals == proposals

    @pytest.mark.asyncio
    async def test_explore_no_matches_returns_empty(self) -> None:
        cocreation = _make_session(status="defined")
        session = _make_mock_session()

        matcher = AsyncMock()
        matcher.match_by_keywords = AsyncMock(return_value=[])

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "app.api.v1.cocreation.ExperienceMatcher",
                lambda s: matcher,
            )
            proposals = await _explore_session(cocreation, session)

        assert cocreation.status == "exploring"
        assert proposals == []
        assert cocreation.agent_proposals == []


# ── _judge_session tests ──


class TestJudgeSession:
    """Test _judge_session logic."""

    @pytest.mark.asyncio
    async def test_judge_accept_creates_experience(self) -> None:
        cocreation = _make_session(status="exploring", agent_proposals=[{"approach": "x"}])
        session = _make_mock_session()

        # Track the experience object added to session
        added_objects: list = []

        async def _flush_side_effect():
            # Simulate DB generating IDs on flush
            for obj in added_objects:
                if hasattr(obj, "id") and obj.id is None:
                    obj.id = uuid.uuid4()

        session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        session.flush = AsyncMock(side_effect=_flush_side_effect)

        data = CoCreationJudgeRequest(accepted=True, feedback="Good work", rating=5)
        result = await _judge_session(cocreation, data, session)

        assert result.status == "completed"
        assert result.human_feedback == "Good work"
        assert result.human_rating == 5
        # An Experience should have been added
        assert len(added_objects) == 1
        assert result.experience_id is not None
        assert result.experience_id == added_objects[0].id

    @pytest.mark.asyncio
    async def test_judge_reject_no_experience(self) -> None:
        cocreation = _make_session(status="exploring", agent_proposals=[{"approach": "x"}])
        session = _make_mock_session()
        session.add = MagicMock()

        data = CoCreationJudgeRequest(accepted=False, feedback="Not good", rating=2)
        result = await _judge_session(cocreation, data, session)

        assert result.status == "rejected"
        assert result.human_feedback == "Not good"
        assert result.human_rating == 2
        assert result.experience_id is None
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_judge_accept_stores_feedback(self) -> None:
        cocreation = _make_session(status="exploring")
        session = _make_mock_session()
        session.add = MagicMock(side_effect=lambda obj: None)

        data = CoCreationJudgeRequest(accepted=True, feedback="Excellent approach", rating=4)
        result = await _judge_session(cocreation, data, session)

        assert result.human_feedback == "Excellent approach"
        assert result.human_rating == 4
        assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_judge_accept_confidence_from_rating(self) -> None:
        cocreation = _make_session(status="exploring")
        session = _make_mock_session()

        added_objects: list = []
        session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        data = CoCreationJudgeRequest(accepted=True, rating=3)
        await _judge_session(cocreation, data, session)

        # rating 3 / 5 = 0.6
        experience = added_objects[0]
        assert experience.confidence_score == pytest.approx(0.6, abs=0.01)
