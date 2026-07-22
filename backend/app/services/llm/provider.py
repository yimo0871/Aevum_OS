"""LLM 服务提供者 - 支持多模型."""
from __future__ import annotations
import logging
from typing import Optional
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMProvider:
    _client: Optional[AsyncOpenAI] = None

    @classmethod
    def get_client(cls) -> Optional[AsyncOpenAI]:
        if cls._client is None:
            api_key = settings.openai_api_key
            if api_key and not api_key.startswith("sk-your") and not api_key.startswith("your-"):
                cls._client = AsyncOpenAI(
                    api_key=api_key,
                    base_url=settings.openai_base_url,
                )
        return cls._client

    @classmethod
    async def generate(cls, prompt: str, system: str = "") -> str:
        """生成文本（如果 LLM 不可用则返回空字符串）."""
        client = cls.get_client()
        if client is None:
            return ""
        try:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            response = await client.chat.completions.create(
                model=settings.llm_model,
                messages=messages,
                temperature=settings.llm_temperature,
                max_tokens=settings.llm_max_tokens,
            )
            return response.choices[0].message.content or ""
        except Exception:
            logger.warning("[LLM] 文本生成失败", exc_info=True)
            return ""

    @classmethod
    def is_available(cls) -> bool:
        """检查 LLM 是否可用."""
        return cls.get_client() is not None
