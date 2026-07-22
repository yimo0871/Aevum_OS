"""Unit tests for LLM re-ranker module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.retrieval.reranker import LLMReranker


class TestLLMReranker:
    def test_init_defaults(self):
        reranker = LLMReranker()
        assert reranker.top_k == 10

    def test_init_custom(self):
        reranker = LLMReranker(top_k=5)
        assert reranker.top_k == 5

    @pytest.mark.asyncio
    async def test_rerank_empty(self):
        reranker = LLMReranker()
        result = await reranker.rerank("query", [])
        assert result == []

    @pytest.mark.asyncio
    async def test_rerank_no_api_key(self):
        """Without API key, returns original order."""
        with patch("app.services.retrieval.reranker.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            mock_settings.llm_model = "gpt-4o-mini"
            reranker = LLMReranker()
            results = [MagicMock(), MagicMock(), MagicMock()]
            result = await reranker.rerank("query", results)
            assert result == results

    @pytest.mark.asyncio
    async def test_rerank_success(self):
        """LLM returns scores, results are re-sorted."""
        with patch("app.services.retrieval.reranker.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"
            mock_settings.llm_model = "gpt-4o-mini"

            reranker = LLMReranker(top_k=3)

            # Mock candidates
            candidates = []
            for i in range(3):
                exp = MagicMock()
                exp.intent = f"experience {i}"
                c = MagicMock()
                c.experience = exp
                candidates.append(c)

            # LLM returns scores in different order
            with patch.object(reranker, '_llm_score', new_callable=AsyncMock, return_value=[3.0, 9.0, 5.0]):
                result = await reranker.rerank("query", candidates)
                # Should be sorted by score descending: [9.0, 5.0, 3.0] -> [1, 2, 0]
                assert result[0] == candidates[1]
                assert result[1] == candidates[2]
                assert result[2] == candidates[0]

    @pytest.mark.asyncio
    async def test_rerank_llm_failure(self):
        """LLM failure returns original order."""
        with patch("app.services.retrieval.reranker.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"
            mock_settings.llm_model = "gpt-4o-mini"

            reranker = LLMReranker()
            candidates = [MagicMock(), MagicMock()]

            with patch.object(reranker, '_llm_score', new_callable=AsyncMock, side_effect=Exception("API error")):
                result = await reranker.rerank("query", candidates)
                assert result == candidates

    @pytest.mark.asyncio
    async def test_rerank_top_k(self):
        """Only top_k candidates are returned."""
        with patch("app.services.retrieval.reranker.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"
            mock_settings.llm_model = "gpt-4o-mini"

            reranker = LLMReranker(top_k=2)
            candidates = [MagicMock() for _ in range(5)]

            with patch.object(reranker, '_llm_score', new_callable=AsyncMock, return_value=[1.0, 2.0]):
                result = await reranker.rerank("query", candidates)
                assert len(result) == 2
