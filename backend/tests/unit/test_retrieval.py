"""Unit tests for retrieval layer."""

import math
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch


class TestHashEmbedder:
    """Test HashEmbedder."""

    def test_deterministic_embedding(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=128)
        vec1 = embedder.embed("deploy fastapi")
        vec2 = embedder.embed("deploy fastapi")

        assert vec1 == vec2
        assert len(vec1) == 128

    def test_different_text_different_vector(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=128)
        vec1 = embedder.embed("deploy fastapi")
        vec2 = embedder.embed("test python code")

        assert vec1 != vec2

    def test_normalization(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=64)
        vec = embedder.embed("some text with multiple words")

        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01  # L2 normalized

    def test_empty_text(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=32)
        vec = embedder.embed("")
        assert len(vec) == 32
        assert all(v == 0.0 for v in vec)


class TestCosineSimilarity:
    """Test cosine similarity computation."""

    def test_identical_vectors(self) -> None:
        from app.services.retrieval.matcher import ExperienceMatcher

        vec = [1.0, 0.0, 0.0]
        sim = ExperienceMatcher.cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors(self) -> None:
        from app.services.retrieval.matcher import ExperienceMatcher

        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        sim = ExperienceMatcher.cosine_similarity(vec_a, vec_b)
        assert abs(sim - 0.0) < 0.001

    def test_opposite_vectors(self) -> None:
        from app.services.retrieval.matcher import ExperienceMatcher

        vec_a = [1.0, 0.0]
        vec_b = [-1.0, 0.0]
        sim = ExperienceMatcher.cosine_similarity(vec_a, vec_b)
        assert abs(sim - (-1.0)) < 0.001

    def test_empty_vectors(self) -> None:
        from app.services.retrieval.matcher import ExperienceMatcher

        assert ExperienceMatcher.cosine_similarity([], []) == 0.0

    def test_different_length(self) -> None:
        from app.services.retrieval.matcher import ExperienceMatcher

        assert ExperienceMatcher.cosine_similarity([1.0], [1.0, 2.0]) == 0.0


class TestExperienceRanker:
    """Test ExperienceRanker - 多因子排序."""

    def _make_experience(
        self,
        success: bool = True,
        confidence: float = 0.8,
        domain: str = "devops",
        days_ago: int = 1,
        provenance: dict | None = None,
    ) -> "Experience":
        from app.models.experience import Experience

        return Experience(
            id=None,
            context={"domain": domain, "task_type": "test"},
            intent="Test intent",
            outcome={"success": success, "metrics": {}},
            confidence_score=confidence,
            provenance=provenance or {},
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )

    def test_rank_by_similarity(self) -> None:
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        exp = self._make_experience()
        match1 = MatchResult(experience=exp, similarity=0.9, matched_fields=["vector"])
        match2 = MatchResult(experience=exp, similarity=0.5, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match1, match2])

        assert results[0].similarity == 0.9
        assert results[1].similarity == 0.5

    def test_success_increases_score(self) -> None:
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        exp_success = self._make_experience(success=True)
        exp_fail = self._make_experience(success=False)

        match1 = MatchResult(experience=exp_success, similarity=0.5, matched_fields=["vector"])
        match2 = MatchResult(experience=exp_fail, similarity=0.5, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match1, match2])

        assert results[0].experience.outcome.get("success") is True

    def test_recency_decay(self) -> None:
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        exp_new = self._make_experience(days_ago=1)
        exp_old = self._make_experience(days_ago=90)

        match1 = MatchResult(experience=exp_new, similarity=0.5, matched_fields=["vector"])
        match2 = MatchResult(experience=exp_old, similarity=0.5, matched_fields=["vector"])

        ranker = ExperienceRanker(recency_half_life_days=30)
        results = ranker.rank([match1, match2])

        assert results[0].factors.recency > results[1].factors.recency

    def test_domain_distance(self) -> None:
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        exp_same = self._make_experience(domain="devops")
        exp_diff = self._make_experience(domain="frontend")

        match1 = MatchResult(experience=exp_same, similarity=0.5, matched_fields=["vector"])
        match2 = MatchResult(experience=exp_diff, similarity=0.5, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match1, match2], query_domain="devops")

        assert results[0].factors.domain_distance == 0.0  # same domain
        assert results[1].factors.domain_distance == 1.0  # different domain

    def test_weight_configuration(self) -> None:
        from app.services.retrieval.ranker import ExperienceRanker

        ranker = ExperienceRanker()
        original = ranker.get_weights()

        ranker.update_weights({"confidence": 0.5})
        assert ranker.get_weights()["confidence"] == 0.5
        assert ranker.get_weights()["context_similarity"] == original["context_similarity"]

    def test_trust_score_factor_computed(self) -> None:
        """信任评分应被计算并影响排序."""
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        # 高信任经验：有使用次数和引用次数
        exp_high_trust = self._make_experience(
            provenance={"usage_count": 50, "citation_count": 10},
        )
        # 低信任经验：无使用和引用
        exp_low_trust = self._make_experience(
            provenance={"usage_count": 0, "citation_count": 0},
        )

        match1 = MatchResult(experience=exp_high_trust, similarity=0.5, matched_fields=["vector"])
        match2 = MatchResult(experience=exp_low_trust, similarity=0.5, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match1, match2])

        assert results[0].factors.trust_score > results[1].factors.trust_score
        assert results[0].experience is exp_high_trust

    def test_decay_factor_applied(self) -> None:
        """衰减因子应作为乘法惩罚降低旧经验得分."""
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        # 新经验（90天内，decay=1.0）
        exp_new = self._make_experience(days_ago=1)
        # 旧经验（超过90天，decay<1.0）
        exp_old = self._make_experience(days_ago=200)

        match1 = MatchResult(experience=exp_new, similarity=0.5, matched_fields=["vector"])
        match2 = MatchResult(experience=exp_old, similarity=0.5, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match1, match2])

        assert results[0].factors.decay_factor == 1.0  # 新经验无衰减
        assert results[1].factors.decay_factor < 1.0   # 旧经验有衰减
        assert results[0].total_score > results[1].total_score

    def test_decay_factor_no_penalty_for_recent(self) -> None:
        """90天内的经验不应有衰减惩罚."""
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        exp = self._make_experience(days_ago=30)
        match = MatchResult(experience=exp, similarity=0.8, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match])

        assert results[0].factors.decay_factor == 1.0

    def test_trust_score_in_factors_dict(self) -> None:
        """trust_score 和 decay_factor 应出现在 factors.to_dict() 中."""
        from app.services.retrieval.matcher import MatchResult
        from app.services.retrieval.ranker import ExperienceRanker

        exp = self._make_experience()
        match = MatchResult(experience=exp, similarity=0.7, matched_fields=["vector"])

        ranker = ExperienceRanker()
        results = ranker.rank([match])

        factors_dict = results[0].factors.to_dict()
        assert "trust_score" in factors_dict
        assert "decay_factor" in factors_dict
        assert factors_dict["trust_score"] >= 0.0
        assert factors_dict["decay_factor"] > 0.0


class TestPriorityLevel:
    """Test PriorityLevel enum."""

    def test_priority_order(self) -> None:
        from app.services.retrieval.priority_chain import PriorityLevel

        assert PriorityLevel.USER < PriorityLevel.COMMUNITY
        assert PriorityLevel.COMMUNITY < PriorityLevel.GLOBAL
        assert PriorityLevel.GLOBAL < PriorityLevel.EXTERNAL

    def test_priority_values(self) -> None:
        from app.services.retrieval.priority_chain import PriorityLevel

        assert int(PriorityLevel.USER) == 1
        assert int(PriorityLevel.COMMUNITY) == 2
        assert int(PriorityLevel.GLOBAL) == 3
        assert int(PriorityLevel.EXTERNAL) == 4


class TestHashEmbedderAsync:
    """Test HashEmbedder async interface."""

    @pytest.mark.asyncio
    async def test_embed_async_returns_same_as_sync(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=64)
        sync_vec = embedder.embed("test text")
        async_vec = await embedder.embed_async("test text")

        assert sync_vec == async_vec

    @pytest.mark.asyncio
    async def test_embed_async_deterministic(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=128)
        vec1 = await embedder.embed_async("hello world")
        vec2 = await embedder.embed_async("hello world")

        assert vec1 == vec2

    def test_dimension_property(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=256)
        assert embedder.dimension == 256


class TestHashEmbedderChinese:
    """Test HashEmbedder with Chinese text."""

    def test_chinese_text_embedding(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=128)
        vec = embedder.embed("部署应用到生产环境")

        assert len(vec) == 128
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01 or norm == 0.0

    def test_chinese_deterministic(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=64)
        vec1 = embedder.embed("测试中文")
        vec2 = embedder.embed("测试中文")

        assert vec1 == vec2

    def test_single_chinese_char(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=32)
        vec = embedder.embed("测")

        assert len(vec) == 32

    def test_mixed_text(self) -> None:
        from app.services.retrieval.embedder import HashEmbedder

        embedder = HashEmbedder(dim=64)
        vec = embedder.embed("deploy 部署 application")

        assert len(vec) == 64


class TestGetEmbedder:
    """Test get_embedder factory."""

    def test_returns_hash_embedder_without_key(self) -> None:
        from app.services.retrieval.embedder import get_embedder, HashEmbedder

        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            mock_settings.embedding_dimension = 1536
            embedder = get_embedder()

        assert isinstance(embedder, HashEmbedder)

    def test_returns_hash_embedder_with_placeholder_key(self) -> None:
        from app.services.retrieval.embedder import get_embedder, HashEmbedder

        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-your-key-here"
            mock_settings.embedding_dimension = 1536
            embedder = get_embedder()

        assert isinstance(embedder, HashEmbedder)

    def test_returns_hash_embedder_with_your_prefix(self) -> None:
        from app.services.retrieval.embedder import get_embedder, HashEmbedder

        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = "your-api-key"
            mock_settings.embedding_dimension = 1536
            embedder = get_embedder()

        assert isinstance(embedder, HashEmbedder)

    def test_returns_openai_embedder_with_real_key(self) -> None:
        from app.services.retrieval.embedder import get_embedder, OpenAIEmbedder

        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = "sk-real-key-12345"
            mock_settings.embedding_model = "text-embedding-3-small"
            mock_settings.embedding_dimension = 1536
            embedder = get_embedder()

        assert isinstance(embedder, OpenAIEmbedder)


class TestOpenAIEmbedder:
    """Test OpenAIEmbedder."""

    def test_dimension(self) -> None:
        from app.services.retrieval.embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(dim=512)
        assert embedder.dimension == 512

    def test_default_model(self) -> None:
        from app.services.retrieval.embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        assert embedder.model == "text-embedding-3-small"
        assert embedder.dimension == 1536

    @pytest.mark.asyncio
    async def test_embed_without_key_falls_back_to_hash(self) -> None:
        from app.services.retrieval.embedder import OpenAIEmbedder

        embedder = OpenAIEmbedder(dim=64)

        with patch("app.services.retrieval.embedder.settings") as mock_settings:
            mock_settings.openai_api_key = ""
            vec = await embedder.embed("test text")

        assert len(vec) == 64
