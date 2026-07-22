"""Unit tests for query expander module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.retrieval.query_expander import QueryExpander


class TestQueryExpander:
    def test_init_defaults(self):
        expander = QueryExpander()
        assert expander.max_expansions == 3

    def test_init_custom(self):
        expander = QueryExpander(max_expansions=5)
        assert expander.max_expansions == 5

    @pytest.mark.asyncio
    async def test_expand_no_api_key(self):
        """Without API key, returns only original query."""
        with patch("app.services.retrieval.query_expander.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            mock_settings.llm_model = "gpt-4o-mini"
            expander = QueryExpander()
            result = await expander.expand("deploy app")
            assert result == ["deploy app"]

    @pytest.mark.asyncio
    async def test_expand_success(self):
        """LLM returns expansions."""
        with patch("app.services.retrieval.query_expander.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"
            mock_settings.llm_model = "gpt-4o-mini"

            expander = QueryExpander(max_expansions=2)
            with patch.object(expander, '_llm_expand', new_callable=AsyncMock, return_value=["how to deploy application", "application deployment guide"]):
                result = await expander.expand("deploy app")
                assert "deploy app" in result
                assert "how to deploy application" in result
                assert "application deployment guide" in result
                assert len(result) <= 3  # original + max_expansions

    @pytest.mark.asyncio
    async def test_expand_dedup(self):
        """Duplicate expansions are removed."""
        with patch("app.services.retrieval.query_expander.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"
            mock_settings.llm_model = "gpt-4o-mini"

            expander = QueryExpander(max_expansions=3)
            with patch.object(expander, '_llm_expand', new_callable=AsyncMock, return_value=["deploy app", "another query"]):
                result = await expander.expand("deploy app")
                # "deploy app" should not be duplicated
                assert result.count("deploy app") == 1
                assert "another query" in result

    @pytest.mark.asyncio
    async def test_expand_failure(self):
        """LLM failure returns only original query."""
        with patch("app.services.retrieval.query_expander.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"
            mock_settings.llm_model = "gpt-4o-mini"

            expander = QueryExpander()
            with patch.object(expander, '_llm_expand', new_callable=AsyncMock, side_effect=Exception("API error")):
                result = await expander.expand("deploy app")
                assert result == ["deploy app"]
