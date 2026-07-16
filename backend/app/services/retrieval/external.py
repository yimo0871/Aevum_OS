"""External search provider - 外部网络搜索（优先级链 Level 4 兜底）.

当用户/社区/全球三级经验检索结果不足时，向外部网络搜索作为兜底。
支持可插拔的外部搜索源，默认实现为 HTTP API 搜索。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import httpx


@dataclass
class ExternalResult:
    """外部搜索结果."""

    title: str
    url: str
    snippet: str
    source: str = "external"
    metadata: dict = field(default_factory=dict)


class ExternalSearchProvider:
    """外部搜索提供者基类."""

    async def search(self, query: str, limit: int = 5) -> list[ExternalResult]:
        """执行外部搜索，返回结果列表."""
        raise NotImplementedError


class HTTPExternalSearchProvider(ExternalSearchProvider):
    """基于 HTTP API 的外部搜索提供者.

    通过环境变量 EXTERNAL_SEARCH_URL 配置外部搜索 API 端点。
    如果未配置，返回空结果（优雅降级）。

    请求格式: GET {EXTERNAL_SEARCH_URL}?q={query}&limit={limit}
    响应格式: [{"title": "...", "url": "...", "snippet": "..."}, ...]
    """

    def __init__(self) -> None:
        self.api_url = os.environ.get("EXTERNAL_SEARCH_URL", "")
        self.timeout = float(os.environ.get("EXTERNAL_SEARCH_TIMEOUT", "10"))

    async def search(self, query: str, limit: int = 5) -> list[ExternalResult]:
        if not self.api_url:
            return []

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(
                    self.api_url,
                    params={"q": query, "limit": limit},
                )
                if resp.status_code != 200:
                    return []

                data = resp.json()
                if not isinstance(data, list):
                    return []

                return [
                    ExternalResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        snippet=item.get("snippet", ""),
                        source=item.get("source", "external"),
                        metadata=item.get("metadata", {}),
                    )
                    for item in data[:limit]
                ]
        except Exception:
            return []


# ── 默认提供者（单例） ──
_default_provider: ExternalSearchProvider | None = None


def get_external_search_provider() -> ExternalSearchProvider:
    """获取默认外部搜索提供者."""
    global _default_provider
    if _default_provider is None:
        _default_provider = HTTPExternalSearchProvider()
    return _default_provider


def set_external_search_provider(provider: ExternalSearchProvider) -> None:
    """注入自定义外部搜索提供者（用于测试或自定义集成）."""
    global _default_provider
    _default_provider = provider
