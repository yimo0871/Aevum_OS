"""Query expander - 查询扩展.

使用 LLM 将原始查询扩展为多个语义等价的查询，
支持多路检索提高召回率。支持 OpenAI 兼容 API。
"""

from __future__ import annotations

import json
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class QueryExpander:
    """查询扩展器.

    使用 LLM 生成查询的多个变体，用于多路检索。

    Args:
        model: LLM 模型名称
        max_expansions: 最大扩展数量
    """

    def __init__(
        self,
        model: str | None = None,
        max_expansions: int = 3,
    ) -> None:
        self.model = model or settings.llm_model
        self.max_expansions = max_expansions

    async def expand(self, query: str) -> list[str]:
        """扩展查询.

        返回原始查询 + LLM 生成的扩展查询。
        如果 LLM 不可用或失败，仅返回原始查询。
        """
        if not settings.openai_api_key:
            return [query]

        try:
            expansions = await self._llm_expand(query)
            # 去重，保留原始查询
            all_queries = [query] + [q for q in expansions if q != query]
            return all_queries[:self.max_expansions + 1]
        except Exception as e:
            logger.warning("[QueryExpander] LLM expansion failed: %s", e)
            return [query]

    async def _llm_expand(self, query: str) -> list[str]:
        """调用 LLM 生成查询变体."""
        import httpx

        prompt = (
            f"将以下查询扩展为 {self.max_expansions} 个语义等价但表达不同的查询，"
            f"用于多路检索提高召回率。\n\n"
            f"原始查询: {query}\n\n"
            f"返回 JSON 数组，如 [\"query1\", \"query2\", ...]。只返回数组。"
        )

        base_url = settings.openai_base_url.rstrip("/")
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": 300,
                },
            )
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()
            return json.loads(content)
