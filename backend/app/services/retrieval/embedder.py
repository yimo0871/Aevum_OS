"""Text embedder - 文本向量化.

将文本转换为向量嵌入，用于经验相似度检索。
优先使用 OpenAI embedding API，无 API Key 时降级为哈希模拟。
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.core.config import settings


class EmbedderProtocol(Protocol):
    """向量化接口."""

    async def embed(self, text: str) -> list[float]:
        """将文本转换为向量."""
        ...

    @property
    def dimension(self) -> int:
        """向量维度."""
        ...


class OpenAIEmbedder:
    """OpenAI embedding 向量化器."""

    def __init__(self, model: str = "text-embedding-3-small", dim: int = 1536) -> None:
        self.model = model
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed(self, text: str) -> list[float]:
        """使用 OpenAI API 生成向量嵌入."""
        import httpx

        api_key = settings.openai_api_key
        if not api_key:
            return HashEmbedder(self._dim).embed(text)

        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.openai.com/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}"},
                json={"input": text, "model": self.model},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]


class HashEmbedder:
    """哈希模拟向量化器（无 API Key 时的降级方案）.

    使用确定性哈希生成伪随机向量。不具备语义理解能力，
    但保证相同文本生成相同向量，可用于功能测试。
    """

    def __init__(self, dim: int = 1536) -> None:
        self._dim = dim

    @property
    def dimension(self) -> int:
        return self._dim

    def embed(self, text: str) -> list[float]:
        """使用哈希生成确定性向量."""
        vector = [0.0] * self._dim

        # 分词：英文用空格分词，中文用字符级 bigram
        words = text.lower().split()
        # 中文 bigram：提取连续中文字符，生成 2-gram
        import re
        chinese_segments = re.findall(r'[\u4e00-\u9fff]+', text)
        for seg in chinese_segments:
            for i in range(len(seg) - 1):
                words.append(seg[i:i + 2])
            if len(seg) == 1:
                words.append(seg)

        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(min(8, self._dim)):
                idx = (h + i * 137) % self._dim
                # 使用哈希值生成 -1 到 1 之间的值
                val = ((h >> (i * 4)) & 0xFF) / 127.5 - 1.0
                vector[idx] += val

        # L2 归一化
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    async def embed_async(self, text: str) -> list[float]:
        """异步接口."""
        return self.embed(text)


# ── 默认向量化器 ──

def get_embedder() -> EmbedderProtocol:
    """获取向量化器实例（根据配置自动选择）."""
    api_key = settings.openai_api_key
    # 排除空值和占位符
    if api_key and not api_key.startswith("sk-your") and not api_key.startswith("your-"):
        return OpenAIEmbedder(
            model=settings.embedding_model,
            dim=settings.embedding_dimension,
        )
    return HashEmbedder(dim=settings.embedding_dimension)
