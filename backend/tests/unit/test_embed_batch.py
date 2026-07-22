"""Unit tests for batch embedding."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.retrieval.embedder import OpenAIEmbedder


class TestEmbedBatch:
    @pytest.mark.asyncio
    async def test_empty_input(self):
        embedder = OpenAIEmbedder()
        result = await embedder.embed_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_no_api_key_uses_hash(self):
        """Without API key, falls back to HashEmbedder."""
        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            embedder = OpenAIEmbedder(dim=64)
            result = await embedder.embed_batch(["hello", "world"])
            assert len(result) == 2
            assert len(result[0]) == 64
            assert len(result[1]) == 64
            # Same text should produce same vector
            result2 = await embedder.embed_batch(["hello"])
            assert result[0] == result2[0]

    @pytest.mark.asyncio
    async def test_batch_api_call(self):
        """With API key, calls embedding API once for all texts."""
        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.openai_base_url = "https://test.com/v1"

            embedder = OpenAIEmbedder(model="test-model", dim=128)

            mock_response = MagicMock()
            mock_response.json.return_value = {
                "data": [
                    {"embedding": [0.1] * 128},
                    {"embedding": [0.2] * 128},
                ]
            }
            mock_response.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient") as mock_client_class:
                mock_client = AsyncMock()
                mock_client.post = AsyncMock(return_value=mock_response)
                mock_client.__aenter__ = AsyncMock(return_value=mock_client)
                mock_client.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_client

                result = await embedder.embed_batch(["hello", "world"])
                assert len(result) == 2
                assert result[0] == [0.1] * 128
                assert result[1] == [0.2] * 128

                # Verify only one API call was made
                mock_client.post.assert_called_once()
