"""Redis cache layer - 检索结果与 embedding 缓存.

使用 Redis 缓存热门检索结果和 embedding，减少重复计算。
无 Redis 时优雅降级（直接返回 None）。
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """获取 Redis 客户端（单例）.

    无 Redis 时返回 None，调用方应处理降级。
    """
    global _redis_client
    if _redis_client is None:
        try:
            _redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password or None,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2,
            )
            await _redis_client.ping()
            logger.info("[Cache] Redis connected: %s:%s", settings.redis_host, settings.redis_port)
        except Exception as e:
            logger.warning("[Cache] Redis unavailable, cache disabled: %s", e)
            _redis_client = None
    return _redis_client


def _cache_key(prefix: str, *args: str) -> str:
    """生成缓存键.

    使用 MD5 哈希参数组合，保证键长度可控。
    """
    raw = ":".join(args)
    hashed = hashlib.md5(raw.encode()).hexdigest()[:16]
    return f"aevum:{prefix}:{hashed}"


async def cache_get(prefix: str, *args: str) -> Optional[Any]:
    """从缓存获取数据.

    Returns:
        缓存的数据（已反序列化），未命中时返回 None
    """
    client = await get_redis()
    if client is None:
        return None
    try:
        key = _cache_key(prefix, *args)
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.debug("[Cache] GET failed: %s", e)
        return None


async def cache_set(
    prefix: str,
    value: Any,
    *args: str,
    ttl: int = 300,
) -> None:
    """写入缓存.

    Args:
        prefix: 缓存前缀（如 "search", "embedding"）
        value: 要缓存的数据（会被 JSON 序列化）
        ttl: 过期时间（秒），默认 5 分钟
        args: 用于生成缓存键的参数
    """
    client = await get_redis()
    if client is None:
        return
    try:
        key = _cache_key(prefix, *args)
        await client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
    except Exception as e:
        logger.debug("[Cache] SET failed: %s", e)


async def cache_invalidate(prefix: str, *args: str) -> None:
    """使缓存失效."""
    client = await get_redis()
    if client is None:
        return
    try:
        key = _cache_key(prefix, *args)
        await client.delete(key)
    except Exception as e:
        logger.debug("[Cache] DELETE failed: %s", e)
