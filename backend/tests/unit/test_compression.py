"""Unit tests for CompressionManager - 经验压缩与遗忘系统."""

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.experience import Experience
from app.services.governance.compression import CompressionManager


# ── Helpers ──


def _make_experience(**overrides) -> Experience:
    """Build an Experience ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        context={"domain": "devops", "task_type": "deployment"},
        intent="Deploy a Python FastAPI application to production",
        execution={"steps": [], "tools": [], "trace": {}},
        outcome={"success": True, "metrics": {}},
        reflection={
            "what_worked": ["Docker multi-stage build"],
            "what_failed": ["Config error"],
            "why": "Standard pattern",
        },
        reusable_patterns=[],
        confidence_score=0.8,
        provenance={"usage_count": 10},
        version=1,
        status="active",
        compressed=False,
        compression_summary=None,
        created_at=datetime.now(timezone.utc) - timedelta(days=100),
    )
    defaults.update(overrides)
    return Experience(**defaults)


def _make_mock_session(get_return=None) -> AsyncMock:
    """Build a mock async session where .get returns get_return."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=get_return)
    session.flush = AsyncMock()
    return session


# ── compress_experience tests ──


class TestCompressExperience:
    """Test CompressionManager.compress_experience."""

    @pytest.mark.asyncio
    async def test_compress_sets_compressed_flag(self) -> None:
        exp = _make_experience(confidence_score=0.8)
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        result = await manager.compress_experience(exp.id, session)

        assert result is exp
        assert exp.compressed is True

    @pytest.mark.asyncio
    async def test_compress_reduces_confidence(self) -> None:
        exp = _make_experience(confidence_score=0.8)
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        await manager.compress_experience(exp.id, session)

        # confidence should be halved
        assert exp.confidence_score == pytest.approx(0.4, abs=0.01)

    @pytest.mark.asyncio
    async def test_compress_stores_summary(self) -> None:
        exp = _make_experience(
            intent="Deploy application",
            reflection={"what_worked": ["Docker"], "what_failed": ["Config"], "why": "x"},
        )
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        await manager.compress_experience(exp.id, session)

        assert exp.compression_summary is not None
        assert "Deploy application" in exp.compression_summary
        assert "Docker" in exp.compression_summary

    @pytest.mark.asyncio
    async def test_compress_records_provenance(self) -> None:
        exp = _make_experience(confidence_score=0.6)
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        await manager.compress_experience(exp.id, session)

        assert "compressed_at" in exp.provenance
        assert exp.provenance["original_confidence"] == 0.6

    @pytest.mark.asyncio
    async def test_compress_not_found_returns_none(self) -> None:
        session = _make_mock_session(get_return=None)

        manager = CompressionManager()
        result = await manager.compress_experience(uuid.uuid4(), session)

        assert result is None

    @pytest.mark.asyncio
    async def test_compress_zero_confidence(self) -> None:
        exp = _make_experience(confidence_score=0.0)
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        await manager.compress_experience(exp.id, session)

        assert exp.confidence_score == 0.0
        assert exp.compressed is True


# ── forget_experience tests ──


class TestForgetExperience:
    """Test CompressionManager.forget_experience."""

    @pytest.mark.asyncio
    async def test_forget_sets_status(self) -> None:
        exp = _make_experience()
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        result = await manager.forget_experience(exp.id, "expired", session)

        assert result is exp
        assert exp.status == "forgotten"

    @pytest.mark.asyncio
    async def test_forget_records_reason(self) -> None:
        exp = _make_experience()
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        await manager.forget_experience(exp.id, "low_quality", session)

        assert exp.provenance["forget_reason"] == "low_quality"
        assert "forgotten_at" in exp.provenance

    @pytest.mark.asyncio
    async def test_forget_invalid_reason_raises(self) -> None:
        exp = _make_experience()
        session = _make_mock_session(get_return=exp)

        manager = CompressionManager()
        with pytest.raises(ValueError, match="无效的遗忘原因"):
            await manager.forget_experience(exp.id, "invalid_reason", session)

    @pytest.mark.asyncio
    async def test_forget_not_found_returns_none(self) -> None:
        session = _make_mock_session(get_return=None)

        manager = CompressionManager()
        result = await manager.forget_experience(uuid.uuid4(), "expired", session)

        assert result is None

    @pytest.mark.asyncio
    async def test_forget_all_valid_reasons(self) -> None:
        for reason in ["expired", "low_quality", "redundant", "zero_reuse"]:
            exp = _make_experience()
            session = _make_mock_session(get_return=exp)

            manager = CompressionManager()
            result = await manager.forget_experience(exp.id, reason, session)

            assert result is not None
            assert exp.status == "forgotten"
            assert exp.provenance["forget_reason"] == reason


# ── auto_cleanup tests ──


class TestAutoCleanup:
    """Test CompressionManager.auto_cleanup."""

    @pytest.mark.asyncio
    async def test_cleanup_forgets_old_low_trust(self) -> None:
        # Old experience with low trust (failed outcome, no usage)
        old_exp = _make_experience(
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
            confidence_score=0.05,
            outcome={"success": False, "metrics": {}},
            provenance={"usage_count": 0},
        )
        session = AsyncMock()
        session.flush = AsyncMock()

        # First execute returns the candidates; second returns reuse count
        candidates_result = MagicMock()
        candidates_result.scalars.return_value.all.return_value = [old_exp]
        reuse_result = MagicMock()
        reuse_result.scalar.return_value = 0
        session.execute = AsyncMock(side_effect=[candidates_result, reuse_result])

        manager = CompressionManager()
        forgotten = await manager.auto_cleanup(session, threshold_days=90, min_trust=0.1, min_reuse=1)

        assert len(forgotten) == 1
        assert forgotten[0].status == "forgotten"
        assert forgotten[0].provenance["forget_reason"] == "zero_reuse"

    @pytest.mark.asyncio
    async def test_cleanup_skips_high_trust(self) -> None:
        # Old experience but high trust
        old_exp = _make_experience(
            created_at=datetime.now(timezone.utc) - timedelta(days=120),
            confidence_score=0.9,
            outcome={"success": True, "metrics": {}},
            provenance={"usage_count": 100},
        )
        session = AsyncMock()
        session.flush = AsyncMock()

        candidates_result = MagicMock()
        candidates_result.scalars.return_value.all.return_value = [old_exp]
        reuse_result = MagicMock()
        reuse_result.scalar.return_value = 0
        session.execute = AsyncMock(side_effect=[candidates_result, reuse_result])

        manager = CompressionManager()
        forgotten = await manager.auto_cleanup(session, threshold_days=90, min_trust=0.1, min_reuse=1)

        assert len(forgotten) == 0
        assert old_exp.status == "active"

    @pytest.mark.asyncio
    async def test_cleanup_empty_candidates(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()

        candidates_result = MagicMock()
        candidates_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=candidates_result)

        manager = CompressionManager()
        forgotten = await manager.auto_cleanup(session)

        assert forgotten == []


# ── find_redundant tests ──


class TestFindRedundant:
    """Test CompressionManager.find_redundant."""

    @pytest.mark.asyncio
    async def test_find_redundant_detects_duplicates(self) -> None:
        exp_a = _make_experience(intent="Deploy a Python FastAPI application to production")
        exp_b = _make_experience(intent="Deploy a Python FastAPI application to production")
        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [exp_a, exp_b]
        session.execute = AsyncMock(return_value=result_mock)

        manager = CompressionManager()
        pairs = await manager.find_redundant("devops", session, similarity_threshold=0.95)

        assert len(pairs) == 1
        assert pairs[0][0] is exp_a
        assert pairs[0][1] is exp_b
        assert pairs[0][2] >= 0.95

    @pytest.mark.asyncio
    async def test_find_redundant_no_duplicates(self) -> None:
        exp_a = _make_experience(intent="Deploy application to production")
        exp_b = _make_experience(intent="Run database migration scripts")
        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [exp_a, exp_b]
        session.execute = AsyncMock(return_value=result_mock)

        manager = CompressionManager()
        pairs = await manager.find_redundant("devops", session, similarity_threshold=0.95)

        assert len(pairs) == 0

    @pytest.mark.asyncio
    async def test_find_redundant_empty_domain(self) -> None:
        session = AsyncMock()

        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        manager = CompressionManager()
        pairs = await manager.find_redundant("nonexistent", session)

        assert pairs == []


# ── Helper method tests ──


class TestCompressionHelpers:
    """Test CompressionManager static helper methods."""

    def test_tokenize(self) -> None:
        tokens = CompressionManager._tokenize("Deploy application to Production!")
        assert "deploy" in tokens
        assert "application" in tokens
        assert "production" in tokens

    def test_tokenize_empty(self) -> None:
        assert CompressionManager._tokenize("") == set()

    def test_jaccard_similarity_identical(self) -> None:
        set_a = {"a", "b", "c"}
        assert CompressionManager._jaccard_similarity(set_a, set_a) == 1.0

    def test_jaccard_similarity_disjoint(self) -> None:
        set_a = {"a", "b"}
        set_b = {"c", "d"}
        assert CompressionManager._jaccard_similarity(set_a, set_b) == 0.0

    def test_jaccard_similarity_partial(self) -> None:
        set_a = {"a", "b", "c"}
        set_b = {"b", "c", "d"}
        # intersection=2, union=4 -> 0.5
        assert CompressionManager._jaccard_similarity(set_a, set_b) == 0.5

    def test_jaccard_similarity_empty(self) -> None:
        assert CompressionManager._jaccard_similarity(set(), {"a"}) == 0.0
