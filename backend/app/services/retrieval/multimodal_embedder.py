"""Multimodal embedder - 多模态向量化.

支持文本、代码、图像描述、音频转录的多模态嵌入。
采用可插拔 provider 设计：
- "local"（默认）：纯本地，无外部 API
- "openai"：当配置了 API Key 时使用 OpenAI embedding

由于图像和音频以文本描述/转录形式输入，本向量化器基于文本嵌入实现。
"""

from __future__ import annotations

import asyncio
import inspect
import math

from app.core.config import settings
from app.services.retrieval.code_embedder import CodeEmbedder
from app.services.retrieval.embedder import HashEmbedder, OpenAIEmbedder


class MultimodalEmbedder:
    """多模态向量化器 - 统一接口支持多种模态.

    文本/图像描述/音频转录使用文本嵌入器（HashEmbedder 或 OpenAIEmbedder），
    代码使用 CodeEmbedder。
    """

    def __init__(self, provider: str = "local") -> None:
        self.provider = provider
        self._text_dim = settings.embedding_dimension

        # 文本嵌入器
        if provider == "openai":
            api_key = settings.openai_api_key
            if api_key and not api_key.startswith("sk-your") and not api_key.startswith("your-"):
                self._text_embedder = OpenAIEmbedder(
                    model=settings.embedding_model,
                    dim=self._text_dim,
                )
            else:
                self._text_embedder = HashEmbedder(dim=self._text_dim)
        else:
            # local provider：始终使用 HashEmbedder
            self._text_embedder = HashEmbedder(dim=self._text_dim)

        # 代码嵌入器
        self._code_embedder = CodeEmbedder()

    @property
    def text_dimension(self) -> int:
        return self._text_dim

    @property
    def code_dimension(self) -> int:
        return self._code_embedder.dimension

    def embed_text(self, text: str) -> list[float]:
        """文本嵌入（委托给文本嵌入器）."""
        return self._sync_embed_text(text)

    def embed_code(self, code: str, language: str = "python") -> list[float]:
        """代码嵌入（委托给 CodeEmbedder）."""
        return self._code_embedder.embed_code(code, language=language)

    def embed_image_description(self, description: str) -> list[float]:
        """图像描述嵌入（基于文本，添加模态前缀以区分）."""
        return self._sync_embed_text(f"[image] {description}")

    def embed_audio_transcript(self, transcript: str) -> list[float]:
        """音频转录嵌入（基于文本，添加模态前缀以区分）."""
        return self._sync_embed_text(f"[audio] {transcript}")

    def embed(self, content: str, modality: str = "text", **kwargs: object) -> list[float]:
        """统一嵌入接口 - 按模态分发.

        Args:
            content: 待嵌入内容
            modality: 模态类型（text/code/image/audio）
            **kwargs: 额外参数（如 code 的 language）

        Returns:
            嵌入向量
        """
        if modality == "text":
            return self.embed_text(content)
        if modality == "code":
            language = kwargs.get("language", "python")
            return self.embed_code(content, language=str(language))
        if modality == "image":
            return self.embed_image_description(content)
        if modality == "audio":
            return self.embed_audio_transcript(content)
        raise ValueError(f"不支持的模态: {modality}")

    @staticmethod
    def compute_similarity(vec1: list[float], vec2: list[float]) -> float:
        """计算两个向量的余弦相似度（不同维度返回 0.0）."""
        if len(vec1) != len(vec2) or len(vec1) == 0:
            return 0.0

        dot = sum(a * b for a, b in zip(vec1, vec2, strict=False))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(b * b for b in vec2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def _sync_embed_text(self, text: str) -> list[float]:
        """同步文本嵌入 - 处理同步/异步嵌入器.

        HashEmbedder.embed 是同步的；OpenAIEmbedder.embed 是异步的，
        对于同步接口降级使用 HashEmbedder。
        """
        embedder = self._text_embedder
        embed_fn = getattr(embedder, "embed", None)

        if embed_fn is None:
            return HashEmbedder(dim=self._text_dim).embed(text)

        # 判断是否为协程函数（OpenAIEmbedder.embed 是 async）
        if inspect.iscoroutinefunction(embed_fn):
            # 异步嵌入器：通过 asyncio.run 调用，保留语义嵌入
            try:
                return asyncio.run(embed_fn(text))
            except RuntimeError:
                # 已在事件循环中（如 Celery worker），降级为 HashEmbedder
                return HashEmbedder(dim=self._text_dim).embed(text)

        return embed_fn(text)
