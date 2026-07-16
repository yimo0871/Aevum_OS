"""Unit tests for PriorityChain - 四级优先级检索链."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.experience import Experience
from app.services.retrieval.priority_chain import (
    PriorityChain,
    PriorityChainResult,
    PriorityLevel,
)
from app.services.retrieval.matcher import MatchResult
from app.services.retrieval.ranker import RankedResult, ScoreFactors


def _make_experience(**overrides) -> Experience:
    defaults = dict(
        id=uuid.uuid4(),
        context={"domain": "devops", "task_type": "deployment"},
        intent="Deploy app",
        outcome={"success": True, "metrics": {}},
        confidence_score=0.8,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Experience(**defaults)


def _make_match_result(similarity: float = 0.8) -> MatchResult:
    return MatchResult(
        experience=_make_experience(),
        similarity=similarity,
        matched_fields=["vector"],
    )


def _make_ranked_result(score: float = 0.8) -> RankedResult:
    return RankedResult(
        experience=_make_experience(),
        total_score=score,
        factors=ScoreFactors(context_similarity=score),
        similarity=score,
    )


class TestPriorityChainResult:
    """Test PriorityChainResult dataclass."""

    def test_to_dict(self) -> None:
        result = PriorityChainResult(
            level=PriorityLevel.USER,
            total_found=5,
            searched=True,
        )
        d = result.to_dict()
        assert d["level"] == "USER"
        assert d["level_value"] == 1
        assert d["total_found"] == 5
        assert d["searched"] is True
        assert d["results"] == []

    def test_to_dict_with_results(self) -> None:
        ranked = _make_ranked_result(0.9)
        result = PriorityChainResult(
            level=PriorityLevel.GLOBAL,
            results=[ranked],
            total_found=1,
            searched=True,
        )
        d = result.to_dict()
        assert len(d["results"]) == 1
        assert "experience_id" in d["results"][0]

    def test_defaults(self) -> None:
        result = PriorityChainResult(level=PriorityLevel.COMMUNITY)
        assert result.results == []
        assert result.total_found == 0
        assert result.searched is False


class TestPriorityChainSearch:
    """Test PriorityChain.search - 四级优先级链."""

    @pytest.mark.asyncio
    async def test_user_level_sufficient(self) -> None:
        """User level has enough results -> only user level searched."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=2, max_results=10)

        # Mock _search_user to return 3 matches
        matches = [_make_match_result() for _ in range(3)]
        chain._search_user = AsyncMock(return_value=matches)
        chain.ranker.rank = MagicMock(return_value=[_make_ranked_result() for _ in range(3)])

        results = await chain.search("query", user_id="user1")

        assert len(results) == 1
        assert results[0].level == PriorityLevel.USER
        assert results[0].searched is True
        assert results[0].total_found == 3

    @pytest.mark.asyncio
    async def test_community_level_fills_gap(self) -> None:
        """User level insufficient -> community level searched."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=3, max_results=10)

        user_matches = [_make_match_result() for _ in range(1)]
        community_matches = [_make_match_result() for _ in range(3)]

        chain._search_user = AsyncMock(return_value=user_matches)
        chain._search_community = AsyncMock(return_value=community_matches)
        chain.ranker.rank = MagicMock(side_effect=[
            [_make_ranked_result() for _ in range(1)],
            [_make_ranked_result() for _ in range(3)],
        ])

        results = await chain.search("query", user_id="user1", community_ids=["comm1"])

        assert len(results) == 2
        assert results[0].level == PriorityLevel.USER
        assert results[1].level == PriorityLevel.COMMUNITY

    @pytest.mark.asyncio
    async def test_global_level_searched(self) -> None:
        """User + community insufficient -> global level searched."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=5, max_results=10)

        chain._search_user = AsyncMock(return_value=[])
        chain._search_community = AsyncMock(return_value=[])
        chain._search_global = AsyncMock(return_value=[_make_match_result() for _ in range(5)])
        chain.ranker.rank = MagicMock(side_effect=[
            [],  # user
            [],  # community
            [_make_ranked_result() for _ in range(5)],  # global
        ])

        results = await chain.search("query", user_id="user1", community_ids=["comm1"])

        assert len(results) == 3
        assert results[2].level == PriorityLevel.GLOBAL
        assert results[2].searched is True

    @pytest.mark.asyncio
    async def test_external_level_as_fallback(self) -> None:
        """All levels insufficient -> external level searched (no results)."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=10, max_results=10)

        chain._search_user = AsyncMock(return_value=[])
        chain._search_community = AsyncMock(return_value=[])
        chain._search_global = AsyncMock(return_value=[])
        chain.ranker.rank = MagicMock(return_value=[])

        results = await chain.search("query", user_id="user1", community_ids=["comm1"])

        assert len(results) == 4
        assert results[3].level == PriorityLevel.EXTERNAL
        assert results[3].searched is True
        assert results[3].total_found == 0

    @pytest.mark.asyncio
    async def test_no_user_id_skips_user_search(self) -> None:
        """No user_id -> user level not searched."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=5, max_results=10)

        chain._search_global = AsyncMock(return_value=[_make_match_result() for _ in range(5)])
        chain.ranker.rank = MagicMock(return_value=[_make_ranked_result() for _ in range(5)])

        results = await chain.search("query")

        # user (not searched), community (not searched), global (searched, sufficient)
        assert len(results) == 3
        assert results[0].level == PriorityLevel.USER
        assert results[0].searched is False
        assert results[1].level == PriorityLevel.COMMUNITY
        assert results[1].searched is False
        assert results[2].level == PriorityLevel.GLOBAL
        assert results[2].searched is True

    @pytest.mark.asyncio
    async def test_no_community_id_skips_community_search(self) -> None:
        """No community_id -> community level not searched."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=5, max_results=10)

        chain._search_user = AsyncMock(return_value=[])
        chain._search_global = AsyncMock(return_value=[_make_match_result() for _ in range(5)])
        chain.ranker.rank = MagicMock(side_effect=[
            [],  # user
            [_make_ranked_result() for _ in range(5)],  # global
        ])

        results = await chain.search("query", user_id="user1")

        assert len(results) == 3
        assert results[1].level == PriorityLevel.COMMUNITY
        assert results[1].searched is False

    @pytest.mark.asyncio
    async def test_global_sufficient_no_external(self) -> None:
        """Global level sufficient -> external not reached."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=3, max_results=10)

        chain._search_user = AsyncMock(return_value=[])
        chain._search_community = AsyncMock(return_value=[])
        chain._search_global = AsyncMock(return_value=[_make_match_result() for _ in range(3)])
        chain.ranker.rank = MagicMock(side_effect=[
            [],  # user
            [],  # community
            [_make_ranked_result() for _ in range(3)],  # global
        ])

        results = await chain.search("query", user_id="u1", community_ids=["c1"])

        assert len(results) == 3
        # External not included
        levels = [r.level for r in results]
        assert PriorityLevel.EXTERNAL not in levels

    @pytest.mark.asyncio
    async def test_domain_filter_passed(self) -> None:
        """Domain filter is passed to search methods."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=1, max_results=10)

        chain._search_user = AsyncMock(return_value=[_make_match_result()])
        chain.ranker.rank = MagicMock(return_value=[_make_ranked_result()])

        await chain.search("query", user_id="u1", domain="devops", task_type="deployment")

        chain._search_user.assert_awaited_once_with("query", "u1", "devops", "deployment")


class TestPriorityChainSearchHelpers:
    """Test PriorityChain internal search methods."""

    @pytest.mark.asyncio
    async def test_search_user_vector_success(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)
        matches = [_make_match_result()]
        chain.matcher.match_by_vector = AsyncMock(return_value=matches)

        result = await chain._search_user("query", "user1", "devops", "deployment")

        assert result == matches
        chain.matcher.match_by_vector.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_search_user_fallback_to_keywords(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)
        chain.matcher.match_by_vector = AsyncMock(side_effect=Exception("vector error"))

        result = await chain._search_user("query", "user1", "devops", None)

        assert result == []

    @pytest.mark.asyncio
    async def test_search_community_vector_success(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)
        matches = [_make_match_result()]
        chain.matcher.match_by_vector = AsyncMock(return_value=matches)

        result = await chain._search_community("query", ["comm1"], "devops", "deployment")

        assert result == matches

    @pytest.mark.asyncio
    async def test_search_community_fallback_empty(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)
        chain.matcher.match_by_vector = AsyncMock(side_effect=Exception("error"))

        result = await chain._search_community("query", ["comm1"], None, None)

        assert result == []

    @pytest.mark.asyncio
    async def test_search_global_vector_success(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)
        matches = [_make_match_result()]
        chain.matcher.match_by_vector = AsyncMock(return_value=matches)

        result = await chain._search_global("query", "devops", "deployment")

        assert result == matches

    @pytest.mark.asyncio
    async def test_search_global_fallback_to_keywords(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)
        chain.matcher.match_by_vector = AsyncMock(side_effect=Exception("error"))
        keyword_matches = [_make_match_result()]
        chain.matcher.match_by_keywords = AsyncMock(return_value=keyword_matches)

        result = await chain._search_global("query", "devops", None)

        assert result == keyword_matches


class TestGetBestResults:
    """Test get_best_results."""

    def test_merge_and_sort(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)

        r1 = _make_ranked_result(0.9)
        r2 = _make_ranked_result(0.5)
        r3 = _make_ranked_result(0.7)

        chain_results = [
            PriorityChainResult(level=PriorityLevel.USER, results=[r1, r2]),
            PriorityChainResult(level=PriorityLevel.COMMUNITY, results=[r3]),
        ]

        best = chain.get_best_results(chain_results, limit=3)

        assert len(best) == 3
        assert best[0].total_score == 0.9
        assert best[1].total_score == 0.7
        assert best[2].total_score == 0.5

    def test_limit_applied(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)

        results = [_make_ranked_result(0.1 * i) for i in range(10)]
        chain_results = [PriorityChainResult(level=PriorityLevel.USER, results=results)]

        best = chain.get_best_results(chain_results, limit=3)

        assert len(best) == 3

    def test_empty_chain(self) -> None:
        session = AsyncMock()
        chain = PriorityChain(session)

        best = chain.get_best_results([], limit=5)

        assert best == []


class TestPriorityChainVisibility:
    """Test visibility filtering in priority chain."""

    @pytest.mark.asyncio
    async def test_community_search_passes_visibility_and_exclude_user(self) -> None:
        """Community search should filter by community+public visibility, exclude own experiences, and pass community_ids."""
        session = AsyncMock()
        chain = PriorityChain(session, min_results=5, max_results=10)
        chain.matcher.match_by_vector = AsyncMock(return_value=[])

        await chain._search_community("query", ["comm1"], "devops", "deployment", exclude_user_id="user1")

        chain.matcher.match_by_vector.assert_awaited_once_with(
            "query", limit=10, domain="devops", task_type="deployment",
            visibility_levels=["community", "public"],
            exclude_user_id="user1",
            community_ids=["comm1"],
        )

    @pytest.mark.asyncio
    async def test_global_search_passes_public_visibility(self) -> None:
        """Global search should filter by public visibility only."""
        session = AsyncMock()
        chain = PriorityChain(session)
        chain.matcher.match_by_vector = AsyncMock(return_value=[])

        await chain._search_global("query", "devops", "deployment")

        chain.matcher.match_by_vector.assert_awaited_once_with(
            "query", limit=10, domain="devops", task_type="deployment",
            visibility_levels=["public"],
        )

    @pytest.mark.asyncio
    async def test_user_search_no_visibility_filter(self) -> None:
        """User search should not filter by visibility (user sees all own experiences)."""
        session = AsyncMock()
        chain = PriorityChain(session)
        chain.matcher.match_by_vector = AsyncMock(return_value=[])

        await chain._search_user("query", "user1", "devops", "deployment")

        chain.matcher.match_by_vector.assert_awaited_once_with(
            "query", limit=10, domain="devops", task_type="deployment",
            user_id="user1",
        )

    @pytest.mark.asyncio
    async def test_global_fallback_keywords_with_visibility(self) -> None:
        """Global fallback to keywords should pass visibility filter."""
        session = AsyncMock()
        chain = PriorityChain(session)
        chain.matcher.match_by_vector = AsyncMock(side_effect=Exception("error"))
        chain.matcher.match_by_keywords = AsyncMock(return_value=[])

        await chain._search_global("query", "devops", None)

        chain.matcher.match_by_keywords.assert_awaited_once_with(
            "query", limit=10, domain="devops",
            visibility_levels=["public"],
        )
