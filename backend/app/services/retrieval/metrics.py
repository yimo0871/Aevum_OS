"""Retrieval quality metrics - 检索质量评估指标.

Standard IR (Information Retrieval) metrics for evaluating search quality:
- precision_at_k: 前 K 个结果中相关的比例
- recall_at_k: 相关结果被检索到的比例
- mean_reciprocal_rank: 第一个相关结果的倒数排名均值
- ndcg_at_k: 归一化折损累积增益（考虑排序位置和分级相关性）
"""

from __future__ import annotations

import math
from typing import Sequence


def precision_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
    k: int = 5,
) -> float:
    """Precision@K - 前 K 个结果中相关的比例.

    Args:
        retrieved_ids: 检索结果 ID 列表（按排序降序）
        relevant_ids: 相关结果 ID 集合
        k: 截断位置

    Returns:
        precision 值 [0, 1]

    Example:
        >>> precision_at_k(["a", "b", "c"], {"b", "d"}, k=3)
        0.333  # 1 out of 3 is relevant
    """
    if k <= 0:
        return 0.0
    top_k = list(retrieved_ids)[:k]
    if not top_k:
        return 0.0
    relevant_in_top = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top / len(top_k)


def recall_at_k(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
    k: int = 5,
) -> float:
    """Recall@K - 相关结果被检索到的比例.

    Args:
        retrieved_ids: 检索结果 ID 列表（按排序降序）
        relevant_ids: 相关结果 ID 集合
        k: 截断位置

    Returns:
        recall 值 [0, 1]

    Example:
        >>> recall_at_k(["a", "b", "c"], {"b", "d"}, k=3)
        0.5  # 1 out of 2 relevant items found
    """
    if not relevant_ids:
        return 0.0
    top_k = list(retrieved_ids)[:k]
    relevant_in_top = sum(1 for rid in top_k if rid in relevant_ids)
    return relevant_in_top / len(relevant_ids)


def mean_reciprocal_rank(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
) -> float:
    """Mean Reciprocal Rank - 第一个相关结果的倒数排名.

    Args:
        retrieved_ids: 检索结果 ID 列表（按排序降序）
        relevant_ids: 相关结果 ID 集合

    Returns:
        MRR 值 [0, 1]（1 = 第一个结果就是相关的）

    Example:
        >>> mean_reciprocal_rank(["a", "b", "c"], {"b"})
        0.5  # "b" is at rank 2, so 1/2 = 0.5
    """
    for i, rid in enumerate(retrieved_ids):
        if rid in relevant_ids:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(
    retrieved_ids: Sequence[str],
    relevance_grades: dict[str, float],
    k: int = 5,
) -> float:
    """NDCG@K - 归一化折损累积增益.

    Args:
        retrieved_ids: 检索结果 ID 列表（按排序降序）
        relevance_grades: ID 到分级相关性分数的映射（如 {"a": 3.0, "b": 1.0}）
        k: 截断位置

    Returns:
        NDCG 值 [0, 1]（1 = 完美排序）

    Example:
        >>> ndcg_at_k(["a", "b", "c"], {"a": 3, "b": 2, "c": 1, "d": 3}, k=3)
        # DCG = 3/log2(2) + 2/log2(3) + 1/log2(4) = 3 + 1.26 + 0.5 = 4.76
        # IDCG = 3/log2(2) + 3/log2(3) + 2/log2(4) = 3 + 1.89 + 1 = 5.89
        # NDCG = 4.76 / 5.89 = 0.808
    """
    if k <= 0:
        return 0.0

    top_k = list(retrieved_ids)[:k]

    # DCG: sum of rel_i / log2(i + 2)  (i is 0-indexed, so position = i+1, log2(i+2))
    dcg = 0.0
    for i, rid in enumerate(top_k):
        rel = relevance_grades.get(rid, 0.0)
        dcg += rel / math.log2(i + 2)

    # IDCG: ideal DCG (sort by relevance descending)
    ideal_rels = sorted(relevance_grades.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_rels):
        idcg += rel / math.log2(i + 2)

    if idcg == 0:
        return 0.0

    return dcg / idcg


def evaluate_retrieval(
    retrieved_ids: Sequence[str],
    relevant_ids: set[str],
    relevance_grades: dict[str, float] | None = None,
    k: int = 5,
) -> dict[str, float]:
    """一次性计算所有检索质量指标.

    Args:
        retrieved_ids: 检索结果 ID 列表
        relevant_ids: 相关结果 ID 集合
        relevance_grades: 可选的分级相关性（用于 NDCG）
        k: 截断位置

    Returns:
        {"precision@k": ..., "recall@k": ..., "mrr": ..., "ndcg@k": ...}
    """
    grades = relevance_grades or {rid: 1.0 for rid in relevant_ids}
    return {
        f"precision@{k}": precision_at_k(retrieved_ids, relevant_ids, k),
        f"recall@{k}": recall_at_k(retrieved_ids, relevant_ids, k),
        "mrr": mean_reciprocal_rank(retrieved_ids, relevant_ids),
        f"ndcg@{k}": ndcg_at_k(retrieved_ids, grades, k),
    }
