"""经验衰减系统 -- 过期/低质经验自动降权."""

from datetime import datetime, timezone

from app.services.governance.trust import TrustScorer


class DecayManager:
    """经验衰减管理."""

    DECAY_THRESHOLD_DAYS = 90  # 90天后开始衰减
    MIN_CONFIDENCE = 0.1       # 最低置信度

    def compute_decay_factor(self, experience) -> float:
        """计算衰减因子 0.0-1.0."""
        if not experience.created_at:
            return 1.0
        age_days = (datetime.now(timezone.utc) - experience.created_at).days
        if age_days <= self.DECAY_THRESHOLD_DAYS:
            return 1.0
        # 线性衰减，每多一天衰减 0.5%
        decay = 1.0 - (age_days - self.DECAY_THRESHOLD_DAYS) * 0.005
        return max(decay, 0.1)  # 最低 0.1

    def get_effective_confidence(self, experience) -> float:
        """获取考虑衰减后的有效置信度."""
        trust_score = TrustScorer().compute(experience)
        decay_factor = self.compute_decay_factor(experience)
        return round(experience.confidence_score * decay_factor * (0.5 + 0.5 * trust_score), 4)
