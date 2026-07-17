"""Unit tests for HumanReviewService and HumanReview model - 人机协同评估."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.evaluation import HumanReview
from app.models.experience import Experience, ExperienceRelation
from app.services.evaluation.human_review import HumanReviewService


# ── Helpers ──


def _make_experience(**overrides) -> Experience:
    """Build an Experience ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        context={"domain": "devops"},
        intent="Deploy application",
        execution={},
        outcome={"success": True},
        reflection={},
        reusable_patterns=[],
        confidence_score=0.5,
        provenance={},
        version=1,
        status="active",
        compressed=False,
        owner_agent_id=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Experience(**defaults)


def _make_review(**overrides) -> HumanReview:
    """Build a HumanReview ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        experience_id=uuid.uuid4(),
        reviewer_id=uuid.uuid4(),
        rating=4,
        notes="Good experience",
        recommend_archive=False,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return HumanReview(**defaults)


def _make_mock_session(get_return=None) -> AsyncMock:
    """Build a mock async session where .get returns get_return."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=get_return)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ── HumanReview model tests ──


class TestHumanReviewModel:
    """Test HumanReview ORM model."""

    def test_creation(self) -> None:
        review = _make_review(rating=5, notes="Excellent")
        assert review.rating == 5
        assert review.notes == "Excellent"

    def test_repr(self) -> None:
        review = _make_review(rating=3)
        repr_str = repr(review)
        assert "HumanReview" in repr_str
        assert "3" in repr_str

    def test_to_dict(self) -> None:
        review = _make_review()
        d = review.to_dict()
        assert d["rating"] == 4
        assert d["id"] == str(review.id)
        assert d["experience_id"] == str(review.experience_id)
        assert d["reviewer_id"] == str(review.reviewer_id)
        assert d["recommend_archive"] is False
        assert "created_at" in d

    def test_to_dict_with_archive(self) -> None:
        review = _make_review(recommend_archive=True, rating=1)
        d = review.to_dict()
        assert d["recommend_archive"] is True
        assert d["rating"] == 1


# ── create_review tests ──


class TestCreateReview:
    """Test HumanReviewService.create_review."""

    @pytest.mark.asyncio
    async def test_create_review_success(self) -> None:
        exp = _make_experience(confidence_score=0.5)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        reviewer_id = uuid.uuid4()
        result = await service.create_review(
            experience_id=exp.id,
            reviewer_id=reviewer_id,
            rating=5,
            session=session,
            notes="Great",
        )

        session.add.assert_called_once()
        assert result.rating == 5
        assert result.notes == "Great"
        assert result.experience_id == exp.id

    @pytest.mark.asyncio
    async def test_create_review_adjusts_trust_upward(self) -> None:
        exp = _make_experience(confidence_score=0.5)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        await service.create_review(
            experience_id=exp.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            session=session,
        )

        # rating 5 -> +0.20
        assert exp.confidence_score == pytest.approx(0.7, abs=0.01)

    @pytest.mark.asyncio
    async def test_create_review_adjusts_trust_downward(self) -> None:
        exp = _make_experience(confidence_score=0.5)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        await service.create_review(
            experience_id=exp.id,
            reviewer_id=uuid.uuid4(),
            rating=1,
            session=session,
        )

        # rating 1 -> -0.20
        assert exp.confidence_score == pytest.approx(0.3, abs=0.01)

    @pytest.mark.asyncio
    async def test_create_review_rating_3_no_change(self) -> None:
        exp = _make_experience(confidence_score=0.5)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        await service.create_review(
            experience_id=exp.id,
            reviewer_id=uuid.uuid4(),
            rating=3,
            session=session,
        )

        assert exp.confidence_score == pytest.approx(0.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_create_review_invalid_rating_raises(self) -> None:
        exp = _make_experience()
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        with pytest.raises(ValueError, match="评分必须在 1-5"):
            await service.create_review(
                experience_id=exp.id,
                reviewer_id=uuid.uuid4(),
                rating=6,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_create_review_experience_not_found_raises(self) -> None:
        session = _make_mock_session(get_return=None)

        service = HumanReviewService()
        with pytest.raises(ValueError, match="经验不存在"):
            await service.create_review(
                experience_id=uuid.uuid4(),
                reviewer_id=uuid.uuid4(),
                rating=5,
                session=session,
            )

    @pytest.mark.asyncio
    async def test_create_review_archive_recommendation_low_rating(self) -> None:
        exp = _make_experience(confidence_score=0.4)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        await service.create_review(
            experience_id=exp.id,
            reviewer_id=uuid.uuid4(),
            rating=2,
            session=session,
            recommend_archive=True,
        )

        assert exp.provenance.get("archive_recommended") is True

    @pytest.mark.asyncio
    async def test_create_review_confidence_clamped_to_zero(self) -> None:
        exp = _make_experience(confidence_score=0.05)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        await service.create_review(
            experience_id=exp.id,
            reviewer_id=uuid.uuid4(),
            rating=1,
            session=session,
        )

        # 0.05 - 0.20 = -0.15 -> clamped to 0.0
        assert exp.confidence_score == 0.0

    @pytest.mark.asyncio
    async def test_create_review_confidence_clamped_to_one(self) -> None:
        exp = _make_experience(confidence_score=0.95)
        session = _make_mock_session(get_return=exp)

        service = HumanReviewService()
        await service.create_review(
            experience_id=exp.id,
            reviewer_id=uuid.uuid4(),
            rating=5,
            session=session,
        )

        # 0.95 + 0.20 = 1.15 -> clamped to 1.0
        assert exp.confidence_score == 1.0


# ── get_reviews tests ──


class TestGetReviews:
    """Test HumanReviewService.get_reviews."""

    @pytest.mark.asyncio
    async def test_get_reviews_returns_list(self) -> None:
        exp_id = uuid.uuid4()
        reviews = [
            _make_review(experience_id=exp_id, rating=4),
            _make_review(experience_id=exp_id, rating=5),
        ]
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = reviews
        session.execute = AsyncMock(return_value=result_mock)

        service = HumanReviewService()
        result = await service.get_reviews(exp_id, session)

        assert len(result) == 2
        assert result == reviews

    @pytest.mark.asyncio
    async def test_get_reviews_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        service = HumanReviewService()
        result = await service.get_reviews(uuid.uuid4(), session)

        assert result == []


# ── get_pending_reviews tests ──


class TestGetPendingReviews:
    """Test HumanReviewService.get_pending_reviews."""

    @pytest.mark.asyncio
    async def test_get_pending_returns_high_usage_low_confidence(self) -> None:
        exp = _make_experience(confidence_score=0.3)
        session = AsyncMock()

        # First execute: candidates query; Second: reuse count query
        candidates_result = MagicMock()
        candidates_result.scalars.return_value.all.return_value = [exp]
        reuse_count_result = MagicMock()
        reuse_count_result.scalar.return_value = 10  # high usage
        session.execute = AsyncMock(side_effect=[candidates_result, reuse_count_result])

        service = HumanReviewService()
        result = await service.get_pending_reviews(session, min_usage=5, max_confidence=0.5)

        assert len(result) == 1
        assert result[0] is exp

    @pytest.mark.asyncio
    async def test_get_pending_filters_low_usage(self) -> None:
        exp = _make_experience(confidence_score=0.3)
        session = AsyncMock()

        candidates_result = MagicMock()
        candidates_result.scalars.return_value.all.return_value = [exp]
        reuse_count_result = MagicMock()
        reuse_count_result.scalar.return_value = 2  # below min_usage
        session.execute = AsyncMock(side_effect=[candidates_result, reuse_count_result])

        service = HumanReviewService()
        result = await service.get_pending_reviews(session, min_usage=5, max_confidence=0.5)

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_get_pending_empty(self) -> None:
        session = AsyncMock()
        candidates_result = MagicMock()
        candidates_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=candidates_result)

        service = HumanReviewService()
        result = await service.get_pending_reviews(session)

        assert result == []


# ── compute_trust_adjustment tests ──


class TestComputeTrustAdjustment:
    """Test HumanReviewService.compute_trust_adjustment."""

    def test_adjustment_rating_1(self) -> None:
        assert HumanReviewService.compute_trust_adjustment(1) == -0.20

    def test_adjustment_rating_2(self) -> None:
        assert HumanReviewService.compute_trust_adjustment(2) == -0.10

    def test_adjustment_rating_3(self) -> None:
        assert HumanReviewService.compute_trust_adjustment(3) == 0.0

    def test_adjustment_rating_4(self) -> None:
        assert HumanReviewService.compute_trust_adjustment(4) == 0.10

    def test_adjustment_rating_5(self) -> None:
        assert HumanReviewService.compute_trust_adjustment(5) == 0.20

    def test_adjustment_invalid_rating(self) -> None:
        assert HumanReviewService.compute_trust_adjustment(99) == 0.0
