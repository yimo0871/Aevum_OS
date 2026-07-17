"""Code search service - 代码经验索引与检索.

为经验中的代码内容建立向量索引，支持基于代码相似度的检索。
使用 CodeEmbedder 进行向量化，索引存储在内存中（MVP）。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.services.retrieval.code_embedder import CodeEmbedder


@dataclass
class CodeIndexEntry:
    """代码索引条目."""

    experience_id: str
    embedding: list[float]
    language: str
    code: str


@dataclass
class CodeSearchResult:
    """代码搜索结果."""

    experience_id: str
    similarity: float
    language: str

    def to_dict(self) -> dict:
        return {
            "experience_id": self.experience_id,
            "similarity": self.similarity,
            "language": self.language,
        }


class CodeSearchService:
    """代码搜索服务 - 索引与检索代码经验.

    使用 CodeEmbedder 生成向量，在内存中维护倒排索引，
    支持基于代码结构相似度的检索。
    """

    def __init__(self, embedder: CodeEmbedder | None = None) -> None:
        self.embedder = embedder or CodeEmbedder()
        self._index: dict[str, CodeIndexEntry] = {}

    def index_code(
        self,
        experience_id: str | uuid.UUID,
        code: str,
        language: str = "python",
    ) -> list[float]:
        """为经验索引代码.

        Args:
            experience_id: 经验 ID
            code: 代码内容
            language: 编程语言

        Returns:
            生成的代码向量
        """
        exp_id = str(experience_id)
        embedding = self.embedder.embed_code(code, language=language)
        self._index[exp_id] = CodeIndexEntry(
            experience_id=exp_id,
            embedding=embedding,
            language=language,
            code=code,
        )
        return embedding

    def search_code(
        self,
        query_code: str,
        language: str = "python",
        limit: int = 5,
        min_similarity: float = 0.0,
    ) -> list[CodeSearchResult]:
        """搜索相似代码经验.

        Args:
            query_code: 查询代码
            language: 目标语言过滤（None 表示不过滤）
            limit: 返回数量上限
            min_similarity: 最低相似度阈值

        Returns:
            按相似度降序排列的搜索结果
        """
        query_vec = self.embedder.embed_code(query_code, language=language)

        results: list[CodeSearchResult] = []
        for entry in self._index.values():
            # 语言过滤（language=None 时不过滤）
            if language is not None and entry.language != language:
                continue

            similarity = CodeEmbedder.compute_similarity(query_vec, entry.embedding)
            if similarity >= min_similarity:
                results.append(
                    CodeSearchResult(
                        experience_id=entry.experience_id,
                        similarity=similarity,
                        language=entry.language,
                    )
                )

        results.sort(key=lambda r: r.similarity, reverse=True)
        return results[:limit]

    def remove(self, experience_id: str | uuid.UUID) -> bool:
        """从索引中移除经验."""
        exp_id = str(experience_id)
        if exp_id in self._index:
            del self._index[exp_id]
            return True
        return False

    def clear(self) -> None:
        """清空索引."""
        self._index.clear()

    @property
    def size(self) -> int:
        """索引中的条目数."""
        return len(self._index)
