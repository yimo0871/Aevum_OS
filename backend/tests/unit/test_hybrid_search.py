"""Unit tests for hybrid search module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.retrieval.hybrid_search import HybridSearchResult, HybridSearcher


class TestHybridSearchResult:
    def test_to_dict(self):
        result = HybridSearchResult(
            experience_id="123",
            vector_score=0.8,
            keyword_score=0.6,
            hybrid_score=0.74,
            experience=MagicMock(),
        )
        d = result.to_dict()
        assert d["experience_id"] == "123"
        assert d["vector_score"] == 0.8
        assert d["keyword_score"] == 0.6
        assert d["hybrid_score"] == 0.74


class TestHybridSearcher:
    def test_init_defaults(self):
        session = MagicMock()
        searcher = HybridSearcher(session)
        assert searcher.alpha == 0.7
        assert searcher.bm25_limit == 20

    def test_init_custom(self):
        session = MagicMock()
        searcher = HybridSearcher(session, alpha=0.5, bm25_limit=10)
        assert searcher.alpha == 0.5
        assert searcher.bm25_limit == 10

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        session = AsyncMock()
        searcher = HybridSearcher(session)
        with patch.object(searcher.matcher, 'match_by_vector', new_callable=AsyncMock, return_value=[]):
            with patch.object(searcher, '_bm25_search', new_callable=AsyncMock, return_value=[]):
                results = await searcher.search("test query")
                assert results == []

    @pytest.mark.asyncio
    async def test_search_vector_only(self):
        """Only vector results, no BM25 matches."""
        session = AsyncMock()
        searcher = HybridSearcher(session)
        mock_exp = MagicMock()
        mock_exp.id = "exp-1"
        mock_match = MagicMock()
        mock_match.experience = mock_exp
        mock_match.similarity = 0.85

        with patch.object(searcher.matcher, 'match_by_vector', new_callable=AsyncMock, return_value=[mock_match]):
            with patch.object(searcher, '_bm25_search', new_callable=AsyncMock, return_value=[]):
                results = await searcher.search("test query")
                assert len(results) == 1
                assert results[0].vector_score == 0.85
                assert results[0].keyword_score == 0.0
                # alpha=0.7, hybrid = 0.7 * 0.85 + 0.3 * 0 = 0.595
                assert results[0].hybrid_score == pytest.approx(0.595, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_keyword_only(self):
        """Only BM25 results, no vector matches."""
        session = AsyncMock()
        searcher = HybridSearcher(session)
        mock_exp = MagicMock()
        mock_exp.id = "exp-1"

        with patch.object(searcher.matcher, 'match_by_vector', new_callable=AsyncMock, return_value=[]):
            with patch.object(searcher, '_bm25_search', new_callable=AsyncMock, return_value=[{"id": "exp-1", "score": 5.0}]):
                with patch.object(searcher, '_fetch_experience', new_callable=AsyncMock, return_value=mock_exp):
                    results = await searcher.search("test query")
                    assert len(results) == 1
                    assert results[0].vector_score == 0.0
                    assert results[0].keyword_score == 1.0  # normalized
                    # alpha=0.7, hybrid = 0.7 * 0 + 0.3 * 1.0 = 0.3
                    assert results[0].hybrid_score == pytest.approx(0.3, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_fusion(self):
        """Both vector and keyword matches."""
        session = AsyncMock()
        searcher = HybridSearcher(session, alpha=0.6)
        mock_exp1 = MagicMock()
        mock_exp1.id = "exp-1"
        mock_exp2 = MagicMock()
        mock_exp2.id = "exp-2"

        mock_match1 = MagicMock()
        mock_match1.experience = mock_exp1
        mock_match1.similarity = 0.9
        mock_match2 = MagicMock()
        mock_match2.experience = mock_exp2
        mock_match2.similarity = 0.5

        bm25_results = [
            {"id": "exp-1", "score": 3.0},
            {"id": "exp-2", "score": 6.0},
        ]

        with patch.object(searcher.matcher, 'match_by_vector', new_callable=AsyncMock, return_value=[mock_match1, mock_match2]):
            with patch.object(searcher, '_bm25_search', new_callable=AsyncMock, return_value=bm25_results):
                results = await searcher.search("test query")
                assert len(results) == 2
                # exp-1: vector=0.9, kw=3/6=0.5, hybrid=0.6*0.9+0.4*0.5=0.74
                # exp-2: vector=0.5, kw=6/6=1.0, hybrid=0.6*0.5+0.4*1.0=0.7
                # exp-1 should be first (0.74 > 0.7)
                assert results[0].experience_id == "exp-1"
                assert results[0].hybrid_score == pytest.approx(0.74, abs=0.01)
                assert results[1].experience_id == "exp-2"
                assert results[1].hybrid_score == pytest.approx(0.70, abs=0.01)

    @pytest.mark.asyncio
    async def test_search_limit(self):
        """Results are limited to the requested limit."""
        session = AsyncMock()
        searcher = HybridSearcher(session)
        matches = []
        for i in range(5):
            mock_exp = MagicMock()
            mock_exp.id = f"exp-{i}"
            mock_match = MagicMock()
            mock_match.experience = mock_exp
            mock_match.similarity = 0.5 + i * 0.1
            matches.append(mock_match)

        with patch.object(searcher.matcher, 'match_by_vector', new_callable=AsyncMock, return_value=matches):
            with patch.object(searcher, '_bm25_search', new_callable=AsyncMock, return_value=[]):
                results = await searcher.search("test", limit=3)
                assert len(results) == 3
