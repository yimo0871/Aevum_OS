"""信任评分系统 - 基于 usage_count, success_rate, citation_count, reuse_rate, stability 计算."""


class TrustScorer:
    """计算经验的信任评分."""

    def compute(self, experience) -> float:
        """计算信任评分 0.0-1.0."""
        usage_count = experience.provenance.get("usage_count", 0) if experience.provenance else 0
        outcome = experience.outcome if experience.outcome else {}
        success_rate = 1.0 if outcome.get("success") else 0.0
        citation_count = experience.provenance.get("citation_count", 0) if experience.provenance else 0
        reuse_rate = min(usage_count / 100, 1.0)  # 归一化
        stability = experience.confidence_score or 0.5

        score = (
            0.25 * min(usage_count / 50, 1.0) +  # 使用次数权重 25%
            0.30 * success_rate +                 # 成功率权重 30%
            0.15 * min(citation_count / 20, 1.0) + # 引用次数权重 15%
            0.15 * reuse_rate +                   # 复用率权重 15%
            0.15 * stability                      # 稳定性权重 15%
        )
        return round(score, 4)
