"""Unit tests for CodeEmbedder and CodeSearchService."""

import math

import pytest

from app.services.retrieval.code_embedder import CodeEmbedder
from app.services.retrieval.code_search import CodeSearchService


SAMPLE_PYTHON = '''\
import os
import sys

class DataProcessor:
    """Process data records."""

    def __init__(self, config):
        self.config = config

    def run(self, items):
        results = []
        for item in items:
            if item.active:
                results.append(self.process(item))
        return results

    def process(self, item):
        return item.value * 2
'''

SAMPLE_PYTHON_2 = '''\
import os
from typing import List

class RecordProcessor:
    def process(self, items):
        results = []
        for item in items:
            if item.active:
                results.append(item.value * 2)
        return results
'''

SAMPLE_JAVASCRIPT = '''\
import fs from 'fs';

class DataHandler {
    constructor(config) {
        this.config = config;
    }

    run(items) {
        const results = [];
        for (const item of items) {
            if (item.active) {
                results.push(this.process(item));
            }
        }
        return results;
    }

    process(item) {
        return item.value * 2;
    }
}
'''


class TestExtractFeatures:
    """Test extract_features."""

    def test_extract_basic_features(self) -> None:
        embedder = CodeEmbedder()
        feats = embedder.extract_features(SAMPLE_PYTHON)

        assert feats["functions"] >= 3
        assert feats["classes"] == 1
        assert feats["imports"] >= 2
        assert feats["complexity"] >= 2
        assert feats["lines"] > 0
        assert feats["code_lines"] > 0

    def test_extract_features_empty_code(self) -> None:
        embedder = CodeEmbedder()
        feats = embedder.extract_features("")

        assert feats["lines"] == 0
        assert feats["functions"] == 0
        assert feats["classes"] == 0
        assert feats["imports"] == 0
        assert feats["complexity"] == 0

    def test_extract_features_whitespace_only(self) -> None:
        embedder = CodeEmbedder()
        feats = embedder.extract_features("   \n   \n  ")

        assert feats["lines"] == 3
        assert feats["code_lines"] == 0
        assert feats["functions"] == 0

    def test_extract_features_complexity_count(self) -> None:
        embedder = CodeEmbedder()
        code = "if x:\n    for i in y:\n        while z:\n            pass"
        feats = embedder.extract_features(code)

        # complexity counts if/for/while
        assert feats["complexity"] >= 4  # 1 base + if + for + while

    def test_extract_features_returns_language(self) -> None:
        embedder = CodeEmbedder()
        feats = embedder.extract_features("x = 1")
        assert feats["language"] == "python"


class TestEmbedCode:
    """Test embed_code."""

    def test_embed_returns_fixed_dimension(self) -> None:
        embedder = CodeEmbedder(dim=64)
        vec = embedder.embed_code(SAMPLE_PYTHON)

        assert len(vec) == 64

    def test_embed_deterministic(self) -> None:
        embedder = CodeEmbedder()
        vec1 = embedder.embed_code(SAMPLE_PYTHON)
        vec2 = embedder.embed_code(SAMPLE_PYTHON)

        assert vec1 == vec2

    def test_embed_normalized(self) -> None:
        embedder = CodeEmbedder(dim=64)
        vec = embedder.embed_code(SAMPLE_PYTHON)

        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01

    def test_embed_empty_code_returns_zero_vector(self) -> None:
        embedder = CodeEmbedder(dim=64)
        vec = embedder.embed_code("")

        assert len(vec) == 64
        assert all(v == 0.0 for v in vec)

    def test_embed_different_code_different_vector(self) -> None:
        embedder = CodeEmbedder()
        vec1 = embedder.embed_code("def foo(): pass")
        vec2 = embedder.embed_code("class Bar: pass")

        assert vec1 != vec2

    def test_embed_similar_code_higher_similarity(self) -> None:
        """结构相似的代码相似度应高于不相似的代码."""
        embedder = CodeEmbedder()
        vec1 = embedder.embed_code(SAMPLE_PYTHON)
        vec2 = embedder.embed_code(SAMPLE_PYTHON_2)
        vec_diff = embedder.embed_code("print('hello world')")

        sim_similar = CodeEmbedder.compute_similarity(vec1, vec2)
        sim_diff = CodeEmbedder.compute_similarity(vec1, vec_diff)

        assert sim_similar > sim_diff

    def test_embed_different_language_different_vector(self) -> None:
        embedder = CodeEmbedder()
        vec_py = embedder.embed_code(SAMPLE_PYTHON, language="python")
        vec_js = embedder.embed_code(SAMPLE_PYTHON, language="javascript")

        assert vec_py != vec_js

    def test_embed_large_code(self) -> None:
        """大段代码应正常生成向量."""
        embedder = CodeEmbedder(dim=64)
        large_code = "\n".join(
            [f"def func_{i}(x):" + "\n    return x" for i in range(200)]
        )
        vec = embedder.embed_code(large_code)

        assert len(vec) == 64
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01


class TestComputeSimilarity:
    """Test compute_similarity."""

    def test_identical_vectors(self) -> None:
        vec = [1.0, 0.0, 0.0, 0.0]
        sim = CodeEmbedder.compute_similarity(vec, vec)

        assert abs(sim - 1.0) < 0.001

    def test_orthogonal_vectors(self) -> None:
        vec_a = [1.0, 0.0]
        vec_b = [0.0, 1.0]
        sim = CodeEmbedder.compute_similarity(vec_a, vec_b)

        assert abs(sim - 0.0) < 0.001

    def test_empty_vectors(self) -> None:
        assert CodeEmbedder.compute_similarity([], []) == 0.0

    def test_different_length_vectors(self) -> None:
        assert CodeEmbedder.compute_similarity([1.0], [1.0, 2.0]) == 0.0

    def test_self_similarity_is_one(self) -> None:
        embedder = CodeEmbedder()
        vec = embedder.embed_code(SAMPLE_PYTHON)
        sim = CodeEmbedder.compute_similarity(vec, vec)

        assert abs(sim - 1.0) < 0.001


class TestCodeSearchService:
    """Test CodeSearchService."""

    def test_index_and_search(self) -> None:
        service = CodeSearchService()
        service.index_code("exp-1", SAMPLE_PYTHON)
        service.index_code("exp-2", "print('hello')")

        results = service.search_code(SAMPLE_PYTHON, limit=5)
        assert len(results) >= 1
        assert results[0].experience_id == "exp-1"
        assert results[0].similarity > 0.99  # 自身最相似

    def test_search_sorted_by_similarity(self) -> None:
        service = CodeSearchService()
        service.index_code("exp-1", SAMPLE_PYTHON)
        service.index_code("exp-2", SAMPLE_PYTHON_2)
        service.index_code("exp-3", "x = 1")

        results = service.search_code(SAMPLE_PYTHON, limit=5)
        sims = [r.similarity for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_search_respects_limit(self) -> None:
        service = CodeSearchService()
        for i in range(10):
            service.index_code(f"exp-{i}", f"def func_{i}(x):\n    return x")

        results = service.search_code("def func_0(x):\n    return x", limit=3)
        assert len(results) == 3

    def test_search_min_similarity_filter(self) -> None:
        service = CodeSearchService()
        service.index_code("exp-1", SAMPLE_PYTHON)
        service.index_code("exp-2", "x = 1")

        results = service.search_code(SAMPLE_PYTHON, min_similarity=0.99)
        assert all(r.similarity >= 0.99 for r in results)

    def test_remove_and_clear(self) -> None:
        service = CodeSearchService()
        service.index_code("exp-1", SAMPLE_PYTHON)

        assert service.size == 1
        assert service.remove("exp-1") is True
        assert service.size == 0
        assert service.remove("exp-1") is False

        service.index_code("exp-2", SAMPLE_PYTHON)
        service.clear()
        assert service.size == 0
