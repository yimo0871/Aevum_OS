"""Unit tests for retrieval quality metrics."""

import pytest
from app.services.retrieval.metrics import (
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    evaluate_retrieval,
)


class TestPrecisionAtK:
    def test_all_relevant(self):
        assert precision_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == 1.0

    def test_none_relevant(self):
        assert precision_at_k(["a", "b", "c"], {"d", "e"}, k=3) == 0.0

    def test_partial(self):
        result = precision_at_k(["a", "b", "c"], {"b", "d"}, k=3)
        assert abs(result - 1 / 3) < 0.001

    def test_k_larger_than_results(self):
        assert precision_at_k(["a", "b"], {"a"}, k=5) == 0.5

    def test_k_zero(self):
        assert precision_at_k(["a", "b"], {"a"}, k=0) == 0.0

    def test_empty_results(self):
        assert precision_at_k([], {"a"}, k=5) == 0.0


class TestRecallAtK:
    def test_all_found(self):
        assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=3) == 1.0

    def test_none_found(self):
        assert recall_at_k(["a", "b"], {"c", "d"}, k=3) == 0.0

    def test_partial(self):
        result = recall_at_k(["a", "b", "c"], {"b", "d"}, k=3)
        assert abs(result - 0.5) < 0.001

    def test_empty_relevant(self):
        assert recall_at_k(["a", "b"], set(), k=3) == 0.0


class TestMeanReciprocalRank:
    def test_first_relevant(self):
        assert mean_reciprocal_rank(["a", "b", "c"], {"a"}) == 1.0

    def test_second_relevant(self):
        assert mean_reciprocal_rank(["a", "b", "c"], {"b"}) == 0.5

    def test_third_relevant(self):
        assert abs(mean_reciprocal_rank(["a", "b", "c"], {"c"}) - 1 / 3) < 0.001

    def test_none_relevant(self):
        assert mean_reciprocal_rank(["a", "b", "c"], {"d"}) == 0.0

    def test_multiple_relevant_first_wins(self):
        assert mean_reciprocal_rank(["a", "b", "c"], {"b", "c"}) == 0.5


class TestNDCGAtK:
    def test_perfect_ranking(self):
        grades = {"a": 3, "b": 2, "c": 1}
        assert abs(ndcg_at_k(["a", "b", "c"], grades, k=3) - 1.0) < 0.001

    def test_worst_ranking(self):
        grades = {"a": 3, "b": 2, "c": 1}
        result = ndcg_at_k(["c", "b", "a"], grades, k=3)
        assert 0 < result < 1.0

    def test_no_relevant(self):
        assert ndcg_at_k(["x", "y"], {"a": 1}, k=3) == 0.0

    def test_k_zero(self):
        assert ndcg_at_k(["a"], {"a": 1}, k=0) == 0.0

    def test_known_values(self):
        # DCG = 3/log2(2) + 2/log2(3) + 0/log2(4) = 3 + 1.262 + 0 = 4.262
        # IDCG = 3/log2(2) + 2/log2(3) + 1/log2(4) = 3 + 1.262 + 0.5 = 4.762
        # NDCG = 4.262 / 4.762 ≈ 0.895
        grades = {"a": 3, "b": 2, "c": 1}
        result = ndcg_at_k(["a", "b", "x"], grades, k=3)
        assert 0.85 < result < 0.95


class TestEvaluateRetrieval:
    def test_returns_all_metrics(self):
        result = evaluate_retrieval(
            ["a", "b", "c"], {"a", "b"}, k=3
        )
        assert "precision@3" in result
        assert "recall@3" in result
        assert "mrr" in result
        assert "ndcg@3" in result

    def test_with_grades(self):
        result = evaluate_retrieval(
            ["a", "b", "c"],
            {"a", "b"},
            relevance_grades={"a": 3, "b": 2, "c": 1},
            k=3,
        )
        assert result["precision@3"] == 2 / 3
        assert result["recall@3"] == 1.0
        assert result["mrr"] == 1.0
        assert 0 < result["ndcg@3"] <= 1.0
