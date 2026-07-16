"""Unit tests for external search provider."""

import pytest
from unittest.mock import AsyncMock, patch

from app.services.retrieval.external import (
    ExternalResult,
    ExternalSearchProvider,
    HTTPExternalSearchProvider,
    get_external_search_provider,
    set_external_search_provider,
)


class TestExternalResult:
    """Test ExternalResult dataclass."""

    def test_creation(self) -> None:
        result = ExternalResult(
            title="Test Result",
            url="https://example.com",
            snippet="A test snippet",
        )
        assert result.title == "Test Result"
        assert result.url == "https://example.com"
        assert result.source == "external"

    def test_with_metadata(self) -> None:
        result = ExternalResult(
            title="Test",
            url="https://example.com",
            snippet="Snippet",
            source="google",
            metadata={"rank": 1},
        )
        assert result.source == "google"
        assert result.metadata == {"rank": 1}


class TestHTTPExternalSearchProvider:
    """Test HTTP external search provider."""

    def test_no_api_url_returns_empty(self) -> None:
        """When EXTERNAL_SEARCH_URL is not set, returns empty list."""
        import os
        old_val = os.environ.pop("EXTERNAL_SEARCH_URL", None)
        try:
            provider = HTTPExternalSearchProvider()
            assert provider.api_url == ""
        finally:
            if old_val:
                os.environ["EXTERNAL_SEARCH_URL"] = old_val

    @pytest.mark.asyncio
    async def test_search_without_api_url(self) -> None:
        """Search without configured API returns empty."""
        import os
        old_val = os.environ.pop("EXTERNAL_SEARCH_URL", None)
        try:
            provider = HTTPExternalSearchProvider()
            results = await provider.search("test query")
            assert results == []
        finally:
            if old_val:
                os.environ["EXTERNAL_SEARCH_URL"] = old_val


class TestExternalSearchProviderInterface:
    """Test the provider interface and singleton management."""

    def test_get_default_provider(self) -> None:
        provider = get_external_search_provider()
        assert isinstance(provider, HTTPExternalSearchProvider)

    def test_set_custom_provider(self) -> None:
        """Test injecting a custom provider."""
        class MockProvider(ExternalSearchProvider):
            async def search(self, query: str, limit: int = 5) -> list[ExternalResult]:
                return [ExternalResult(title="mock", url="http://mock", snippet="mock")]

        original = get_external_search_provider()
        mock = MockProvider()
        set_external_search_provider(mock)
        try:
            assert get_external_search_provider() is mock
        finally:
            set_external_search_provider(original)


class TestPriorityChainExternal:
    """Test external search integration in priority chain."""

    @pytest.mark.asyncio
    async def test_external_search_returns_results(self) -> None:
        """Priority chain Level 4 should return external results when configured."""
        from unittest.mock import MagicMock
        from app.services.retrieval.priority_chain import PriorityChain

        class MockProvider(ExternalSearchProvider):
            async def search(self, query: str, limit: int = 5) -> list[ExternalResult]:
                return [
                    ExternalResult(title="External Result", url="http://ext.com", snippet="Found externally"),
                ]

        set_external_search_provider(MockProvider())
        try:
            session = MagicMock()
            chain = PriorityChain(session, min_results=1, max_results=5)
            results = await chain._search_external("test query", None, None)

            assert len(results) == 1
            assert results[0].experience.intent == "External Result"
            assert results[0].matched_fields == ["external"]
        finally:
            # Restore default
            set_external_search_provider(HTTPExternalSearchProvider())

    @pytest.mark.asyncio
    async def test_external_search_graceful_degradation(self) -> None:
        """External search returns empty when no API configured (no crash)."""
        from unittest.mock import MagicMock
        from app.services.retrieval.priority_chain import PriorityChain

        # Ensure no API URL is set
        import os
        old_val = os.environ.pop("EXTERNAL_SEARCH_URL", None)
        set_external_search_provider(HTTPExternalSearchProvider())
        try:
            session = MagicMock()
            chain = PriorityChain(session)
            results = await chain._search_external("test", None, None)
            assert results == []
        finally:
            if old_val:
                os.environ["EXTERNAL_SEARCH_URL"] = old_val
