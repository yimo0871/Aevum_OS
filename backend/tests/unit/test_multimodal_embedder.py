"""Unit tests for MultimodalEmbedder."""

import math
from unittest.mock import patch

import pytest

from app.services.retrieval.multimodal_embedder import MultimodalEmbedder


class TestEmbedText:
    """Test embed_text."""

    def test_embed_text_returns_vector(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_text("deploy fastapi application")

        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_embed_text_deterministic(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec1 = emb.embed_text("hello world")
        vec2 = emb.embed_text("hello world")

        assert vec1 == vec2

    def test_embed_text_normalized(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_text("some meaningful text content")

        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01 or norm == 0.0


class TestEmbedCode:
    """Test embed_code."""

    def test_embed_code_returns_vector(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_code("def foo():\n    return 42")

        assert isinstance(vec, list)
        assert len(vec) == emb.code_dimension

    def test_embed_code_with_language(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_py = emb.embed_code("def foo(): pass", language="python")
        vec_js = emb.embed_code("function foo() {}", language="javascript")

        assert len(vec_py) == len(vec_js)
        assert vec_py != vec_js


class TestEmbedImageAndAudio:
    """Test embed_image_description and embed_audio_transcript."""

    def test_embed_image_description(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_image_description("a diagram showing system architecture")

        assert isinstance(vec, list)
        assert len(vec) == emb.text_dimension

    def test_embed_audio_transcript(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_audio_transcript("the user requested deployment")

        assert isinstance(vec, list)
        assert len(vec) == emb.text_dimension

    def test_image_differs_from_plain_text(self) -> None:
        """图像描述应与纯文本产生不同向量（模态前缀区分）."""
        emb = MultimodalEmbedder(provider="local")
        vec_image = emb.embed_image_description("system architecture")
        vec_text = emb.embed_text("system architecture")

        assert vec_image != vec_text

    def test_audio_differs_from_plain_text(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_audio = emb.embed_audio_transcript("deployment request")
        vec_text = emb.embed_text("deployment request")

        assert vec_audio != vec_text


class TestUnifiedInterface:
    """Test unified embed() interface."""

    def test_embed_text_modality(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_unified = emb.embed("hello", modality="text")
        vec_direct = emb.embed_text("hello")

        assert vec_unified == vec_direct

    def test_embed_code_modality(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_unified = emb.embed("def foo(): pass", modality="code")
        vec_direct = emb.embed_code("def foo(): pass")

        assert vec_unified == vec_direct

    def test_embed_image_modality(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_unified = emb.embed("a chart", modality="image")
        vec_direct = emb.embed_image_description("a chart")

        assert vec_unified == vec_direct

    def test_embed_audio_modality(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_unified = emb.embed("transcript text", modality="audio")
        vec_direct = emb.embed_audio_transcript("transcript text")

        assert vec_unified == vec_direct

    def test_embed_default_modality_is_text(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec_default = emb.embed("some content")
        vec_text = emb.embed_text("some content")

        assert vec_default == vec_text

    def test_embed_code_with_language_kwarg(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed("function foo() {}", modality="code", language="javascript")
        vec_direct = emb.embed_code("function foo() {}", language="javascript")

        assert vec == vec_direct

    def test_embed_unsupported_modality_raises(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        with pytest.raises(ValueError, match="不支持"):
            emb.embed("content", modality="video")


class TestComputeSimilarity:
    """Test compute_similarity."""

    def test_identical_vectors(self) -> None:
        vec = [1.0, 0.0, 0.0]
        sim = MultimodalEmbedder.compute_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors(self) -> None:
        sim = MultimodalEmbedder.compute_similarity([1.0, 0.0], [0.0, 1.0])
        assert abs(sim - 0.0) < 0.001

    def test_different_length_returns_zero(self) -> None:
        sim = MultimodalEmbedder.compute_similarity([1.0, 2.0], [1.0])
        assert sim == 0.0

    def test_empty_vectors(self) -> None:
        assert MultimodalEmbedder.compute_similarity([], []) == 0.0

    def test_cross_modal_similarity_is_zero(self) -> None:
        """不同维度（文本 vs 代码）的向量相似度应为 0."""
        emb = MultimodalEmbedder(provider="local")
        text_vec = emb.embed_text("hello")
        code_vec = emb.embed_code("def foo(): pass")

        sim = MultimodalEmbedder.compute_similarity(text_vec, code_vec)
        assert sim == 0.0

    def test_similar_text_higher_similarity(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec1 = emb.embed_text("deploy fastapi to production")
        vec2 = emb.embed_text("deploy fastapi to production")
        vec3 = emb.embed_text("cook pasta recipe")

        sim_same = MultimodalEmbedder.compute_similarity(vec1, vec2)
        sim_diff = MultimodalEmbedder.compute_similarity(vec1, vec3)

        assert sim_same > sim_diff


class TestProviderSelection:
    """Test provider configuration."""

    def test_local_provider_uses_hash_embedder(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        emb = MultimodalEmbedder(provider="local")
        assert isinstance(emb._text_embedder, HashEmbedder)

    def test_openai_provider_without_key_falls_back(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        with patch("app.services.retrieval.multimodal_embedder.settings") as mock:
            mock.openai_api_key = ""
            mock.embedding_dimension = 1536
            mock.embedding_model = "text-embedding-3-small"
            emb = MultimodalEmbedder(provider="openai")

        assert isinstance(emb._text_embedder, HashEmbedder)

    def test_get_multimodal_embedder_factory(self) -> None:
        from app.services.retrieval.embedder import get_multimodal_embedder

        emb = get_multimodal_embedder()
        assert isinstance(emb, MultimodalEmbedder)
        assert emb.provider == "local"

        emb2 = get_multimodal_embedder(provider="openai")
        assert emb2.provider == "openai"


class TestEdgeCases:
    """Test edge cases."""

    def test_embed_empty_text(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_text("")

        assert isinstance(vec, list)
        assert all(v == 0.0 for v in vec)

    def test_embed_empty_code(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_code("")

        assert all(v == 0.0 for v in vec)

    def test_embed_empty_image_description(self) -> None:
        emb = MultimodalEmbedder(provider="local")
        vec = emb.embed_image_description("")

        assert isinstance(vec, list)
