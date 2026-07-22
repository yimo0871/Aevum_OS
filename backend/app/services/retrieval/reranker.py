"""LLM Re-ranker - 基于大语言模型的结果重排.

对检索 top-K 结果，使用 LLM 对每条结果与查询的相关性进行评分，
然后按 LLM 评分重新排序。支持 OpenAI 兼容 API（含火山引擎）。
"""

from __future__ import annotations

import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMReranker:
    """LLM 重排器.

    对 top-K 检索结果使用 LLM 重新评分排序。

    Args:
        model: LLM 模型名称
        top_k: 重排的候选数量
    """

    def __init__(
        self,
        model: str | None = None,
        top_k: int = 10,
    ) -> None:
        self.model = model or settings.llm_model
        self.top_k = top_k

    async def rerank(
        self,
        query: str,
        results: list,  # list[RankedResult] 或 list[HybridSearchResult]
    ) -> list:
        """对结果进行 LLM 重排.

        1. 取 top-K 候选
        2. 构建提示词，让 LLM 对每条结果评分 (0-10)
        3. 按 LLM 评分降序排列
        4. 失败时优雅降级（返回原始顺序）
        """
        if not results:
            return results

        # 取 top-K
        candidates = results[:self.top_k]

        # 检查是否有 LLM API
        if not settings.openai_api_key:
            logger.debug("[Reranker] No LLM API key, skipping rerank")
            return candidates

        try:
            scores = await self._llm_score(query, candidates)
            # 将 LLM 分数附加到结果上并排序
            scored = list(zip(candidates, scores))
            scored.sort(key=lambda x: x[1], reverse=True)
            return [item[0] for item in scored]
        except Exception as e:
            logger.warning("[Reranker] LLM rerank failed, returning original order: %s", e)
            return candidates

    async def _llm_score(self, query: str, candidates: list) -> list[float]:
        """调用 LLM 对候选结果评分."""
        import httpx

        # 构建候选摘要
        candidate_texts = []
        for i, c in enumerate(candidates):
            exp = getattr(c, "experience", c)
            intent = getattr(exp, "intent", str(exp))
            candidate_texts.append(f"[{i}] {intent}")

        prompt = (
            f"查询: {query}\n\n"
            f"候选经验:\n" + "\n".join(candidate_texts) + "\n\n"
            f"请对每条候选经验与查询的相关性评分 (0.0-10.0)，"
            f"返回 JSON 数组，如 [8.5, 3.2, ...]。只返回数组，不要其他内容。"
        )

        base_url = settings.openai_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.0,
                    "max_tokens": 500,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            # 解析 JSON 数组
            scores = json.loads(content)
            return [float(s) for s in scores]
