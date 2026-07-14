"""Unit tests for retrieval layer."""

import math
import pytest
from datetime import datetime, timezone, timedelta


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
    ) -> "Experience":
        from app.models.experience import Experience

        return Experience(
            id=None,
            context={"domain": domain, "task_type": "test"},
            intent="Test intent",
            outcome={"success": success, "metrics": {}},
            confidence_score=confidence,
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


class TestPriorityLevel:
    """Test PriorityLevel enum."""

    def test_priority_order(self) -> None:
        from app.services.retrieval.priority_chain import PriorityLevel

        assert PriorityLevel.USER < PriorityLevel.COMMUNITY
        assert PriorityLevel.COMMUNITY < PriorityLevel.GLOBAL
        assert PriorityLevel.GLOBAL < PriorityLevel.EXTERNAL
