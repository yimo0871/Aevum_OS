"""Unit tests for Redis cache layer."""

import pytest
from unittest.mock import AsyncMock, patch

from app.core.cache import cache_get, cache_set, cache_invalidate, _cache_key


class TestCacheKey:
    def test_consistent_key(self):
        key1 = _cache_key("search", "deploy", "frontend")
        key2 = _cache_key("search", "deploy", "frontend")
        assert key1 == key2

    def test_different_args(self):
        key1 = _cache_key("search", "deploy")
        key2 = _cache_key("search", "deploy", "frontend")
        assert key1 != key2

    def test_key_prefix(self):
        key = _cache_key("embedding", "test text")
        assert key.startswith("aevum:embedding:")


class TestCacheGet:
    @pytest.mark.asyncio
    async def test_get_no_redis(self):
        """No Redis returns None."""
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            result = await cache_get("search", "query")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_cache_hit(self):
        """Cache hit returns deserialized data."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value='{"key": "value"}')
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            result = await cache_get("search", "query")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_cache_miss(self):
        """Cache miss returns None."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=None)
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            result = await cache_get("search", "query")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_error_returns_none(self):
        """Redis error returns None (graceful degradation)."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            result = await cache_get("search", "query")
            assert result is None


class TestCacheSet:
    @pytest.mark.asyncio
    async def test_set_no_redis(self):
        """No Redis, set is a no-op."""
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            await cache_set("search", {"data": 1}, "query")  # should not raise

    @pytest.mark.asyncio
    async def test_set_success(self):
        """Set writes to Redis with TTL."""
        mock_client = AsyncMock()
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            await cache_set("search", {"data": 1}, "query", ttl=60)
            mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_error_no_raise(self):
        """Redis error doesn't raise."""
        mock_client = AsyncMock()
        mock_client.setex = AsyncMock(side_effect=Exception("Write error"))
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            await cache_set("search", {"data": 1}, "query")  # should not raise


class TestCacheInvalidate:
    @pytest.mark.asyncio
    async def test_invalidate_no_redis(self):
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=None):
            await cache_invalidate("search", "query")  # should not raise

    @pytest.mark.asyncio
    async def test_invalidate_success(self):
        mock_client = AsyncMock()
        with patch("app.core.cache.get_redis", new_callable=AsyncMock, return_value=mock_client):
            await cache_invalidate("search", "query")
            mock_client.delete.assert_called_once()
