"""Unit tests for ExperienceMatcher - 向量/关键词匹配."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.experience import Experience
from app.services.retrieval.matcher import ExperienceMatcher, MatchResult


def _make_experience(**overrides) -> Experience:
    defaults = dict(
        id=uuid.uuid4(),
        context={"domain": "devops", "task_type": "deployment"},
        intent="Deploy FastAPI application to production",
        execution={"steps": [], "tools": [], "trace": {}},
        outcome={"success": True, "metrics": {}},
        reflection={"what_worked": [], "what_failed": [], "why": ""},
        reusable_patterns=[],
        confidence_score=0.8,
        provenance={"agent_signals": []},
        version=1,
        evaluation_status="evaluated",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Experience(**defaults)


class TestMatchByVector:
    """Test match_by_vector."""

    @pytest.mark.asyncio
    async def test_match_by_vector_with_results(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()

        # Mock row returned from raw SQL
        mock_row = (
            exp_id,                                    # id
            datetime.now(timezone.utc),                # timestamp
            {"domain": "devops", "task_type": "dep"},  # context
            "Deploy app",                              # intent
            {"steps": []},                             # execution
            {"success": True},                         # outcome
            {"what_worked": []},                       # reflection
            [],                                        # reusable_patterns
            0.9,                                       # confidence_score
            {"agent_signals": []},                     # provenance
            1,                                         # version
            "evaluated",                               # evaluation_status
            datetime.now(timezone.utc),                # created_at
            datetime.now(timezone.utc),                # updated_at
            "private",                                 # visibility
            None,                                      # user_id
            None,                                      # community_id
            0.85,                                      # similarity
        )

        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)

        # Patch the embedder to return a simple vector
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2, 0.3])
            matches = await matcher.match_by_vector("deploy app")

        assert len(matches) == 1
        assert isinstance(matches[0], MatchResult)
        assert matches[0].similarity == 0.85
        assert matches[0].matched_fields == ["vector"]
        assert str(matches[0].experience.id) == str(exp_id)

    @pytest.mark.asyncio
    async def test_match_by_vector_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.fetchall.return_value = []
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2])
            matches = await matcher.match_by_vector("nothing matches")

        assert matches == []

    @pytest.mark.asyncio
    async def test_match_by_vector_with_filters(self) -> None:
        session = AsyncMock()
        mock_row = (
            uuid.uuid4(), datetime.now(timezone.utc), {"domain": "devops"},
            "Deploy", {}, {"success": True}, {}, [], 0.8, {}, 1, "evaluated",
            datetime.now(timezone.utc), datetime.now(timezone.utc),
            "private", None, None, 0.7,
        )
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2])
            matches = await matcher.match_by_vector(
                "query", domain="devops", task_type="deployment", min_similarity=0.5
            )

        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_match_by_vector_null_similarity(self) -> None:
        session = AsyncMock()
        mock_row = (
            uuid.uuid4(), datetime.now(timezone.utc), {"domain": "devops"},
            "Deploy", {}, {"success": True}, {}, [], 0.8, {}, 1, "evaluated",
            datetime.now(timezone.utc), datetime.now(timezone.utc),
            "private", None, None, None,  # null community_id, null similarity
        )
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2])
            matches = await matcher.match_by_vector("query")

        assert matches[0].similarity == 0.0

    @pytest.mark.asyncio
    async def test_match_by_vector_async_embedder(self) -> None:
        """Test that embed_async is used when available."""
        session = AsyncMock()
        mock_row = (
            uuid.uuid4(), datetime.now(timezone.utc), {"domain": "devops"},
            "Deploy", {}, {"success": True}, {}, [], 0.8, {}, 1, "evaluated",
            datetime.now(timezone.utc), datetime.now(timezone.utc),
            "private", None, None, 0.9,
        )
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2, 0.3])
            matches = await matcher.match_by_vector("query")

        mock_embedder.embed_async.assert_awaited_once()
        assert len(matches) == 1


class TestMatchByKeywords:
    """Test match_by_keywords."""

    @pytest.mark.asyncio
    async def test_keyword_match(self) -> None:
        session = AsyncMock()
        exp = _make_experience(intent="deploy fastapi to production")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [exp]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        matches = await matcher.match_by_keywords("deploy fastapi")

        assert len(matches) == 1
        assert matches[0].matched_fields == ["intent"]
        assert matches[0].similarity > 0

    @pytest.mark.asyncio
    async def test_keyword_no_match(self) -> None:
        session = AsyncMock()
        exp = _make_experience(intent="deploy fastapi to production")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [exp]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        matches = await matcher.match_by_keywords("cooking recipe")

        assert matches == []

    @pytest.mark.asyncio
    async def test_keyword_partial_match(self) -> None:
        session = AsyncMock()
        exp = _make_experience(intent="deploy fastapi application")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [exp]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        # "deploy" matches, "recipe" doesn't -> 1/2 = 0.5
        matches = await matcher.match_by_keywords("deploy recipe")

        assert len(matches) == 1
        assert abs(matches[0].similarity - 0.5) < 0.01

    @pytest.mark.asyncio
    async def test_keyword_with_domain_filter(self) -> None:
        session = AsyncMock()
        exp = _make_experience(intent="deploy app")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [exp]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        matches = await matcher.match_by_keywords("deploy", domain="devops")

        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_keyword_sorted_by_similarity(self) -> None:
        session = AsyncMock()
        exp1 = _make_experience(intent="deploy deploy deploy")
        exp2 = _make_experience(intent="deploy something")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [exp1, exp2]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        matches = await matcher.match_by_keywords("deploy")

        assert len(matches) == 2
        assert matches[0].similarity >= matches[1].similarity

    @pytest.mark.asyncio
    async def test_keyword_empty_query(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        matches = await matcher.match_by_keywords("")

        assert matches == []

    @pytest.mark.asyncio
    async def test_keyword_limit_applied(self) -> None:
        session = AsyncMock()
        exps = [_make_experience(intent=f"deploy task {i}") for i in range(15)]

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = exps
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        matches = await matcher.match_by_keywords("deploy", limit=5)

        assert len(matches) == 5


class TestMatchResultToDict:
    """Test MatchResult.to_dict."""

    def test_to_dict(self) -> None:
        exp = _make_experience()
        result = MatchResult(experience=exp, similarity=0.85, matched_fields=["vector", "intent"])
        d = result.to_dict()

        assert d["experience_id"] == str(exp.id)
        assert d["similarity"] == 0.85
        assert d["matched_fields"] == ["vector", "intent"]


class TestMatchByVectorVisibility:
    """Test visibility filtering in match_by_vector."""

    @pytest.mark.asyncio
    async def test_visibility_levels_filter_applied(self) -> None:
        session = AsyncMock()
        mock_row = (
            uuid.uuid4(), datetime.now(timezone.utc), {"domain": "devops"},
            "Deploy", {}, {"success": True}, {}, [], 0.8, {}, 1, "evaluated",
            datetime.now(timezone.utc), datetime.now(timezone.utc),
            "public", None, None, 0.9,
        )
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2])
            matches = await matcher.match_by_vector(
                "query", visibility_levels=["public", "community"]
            )

        assert len(matches) == 1
        assert matches[0].experience.visibility == "public"

    @pytest.mark.asyncio
    async def test_exclude_user_id_filter_applied(self) -> None:
        session = AsyncMock()
        mock_row = (
            uuid.uuid4(), datetime.now(timezone.utc), {"domain": "devops"},
            "Deploy", {}, {"success": True}, {}, [], 0.8, {}, 1, "evaluated",
            datetime.now(timezone.utc), datetime.now(timezone.utc),
            "public", None, None, 0.9,
        )
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2])
            matches = await matcher.match_by_vector(
                "query", exclude_user_id="user-123"
            )

        assert len(matches) == 1

    @pytest.mark.asyncio
    async def test_community_ids_filter_applied(self) -> None:
        """community_ids 参数应正确过滤社区经验."""
        session = AsyncMock()
        mock_row = (
            uuid.uuid4(), datetime.now(timezone.utc), {"domain": "devops"},
            "Deploy", {}, {"success": True}, {}, [], 0.8, {}, 1, "evaluated",
            datetime.now(timezone.utc), datetime.now(timezone.utc),
            "community", None, "comm-1", 0.9,
        )
        result_mock = MagicMock()
        result_mock.fetchall.return_value = [mock_row]
        session.execute.return_value = result_mock

        matcher = ExperienceMatcher(session)
        with patch.object(matcher, "embedder") as mock_embedder:
            mock_embedder.embed_async = AsyncMock(return_value=[0.1, 0.2])
            matches = await matcher.match_by_vector(
                "query", community_ids=["comm-1", "comm-2"]
            )

        assert len(matches) == 1
        assert matches[0].experience.community_id == "comm-1"
