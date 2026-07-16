"""SDK 数据模型 - 简化的 Experience 和搜索结果."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SearchResult:
    """经验搜索结果."""

    id: str
    intent: str
    similarity: float
    confidence_score: float
    domain: str
    task_type: str
    success: bool
    what_worked: list[str]
    what_failed: list[str]
    why: str
    reusable_patterns: list[dict]
    tools: list[str]

    @classmethod
    def from_api(cls, data: dict) -> SearchResult:
        """从 API 响应构建."""
        ctx = data.get("context", {})
        outcome = data.get("outcome", {})
        refl = data.get("reflection", {})
        exec_data = data.get("execution", {})
        return cls(
            id=data.get("id", ""),
            intent=data.get("intent", ""),
            similarity=data.get("similarity", 0.0),
            confidence_score=data.get("confidence_score", 0.0),
            domain=ctx.get("domain", ""),
            task_type=ctx.get("task_type", ""),
            success=outcome.get("success", False),
            what_worked=refl.get("what_worked", []),
            what_failed=refl.get("what_failed", []),
            why=refl.get("why", ""),
            reusable_patterns=data.get("reusable_patterns", []),
            tools=exec_data.get("tools", []),
        )

    def summary(self) -> str:
        """生成经验摘要供 Agent 参考."""
        lines = [f"[{self.similarity:.0%} match] {self.intent}"]
        if self.what_worked:
            lines.append(f"  worked: {', '.join(self.what_worked)}")
        if self.what_failed:
            lines.append(f"  failed: {', '.join(self.what_failed)}")
        if self.tools:
            lines.append(f"  tools: {', '.join(self.tools)}")
        if self.why:
            lines.append(f"  why: {self.why}")
        return "\n".join(lines)


@dataclass
class Experience:
    """经验对象 - 用于创建经验时的数据容器."""

    context: dict[str, Any]
    intent: str
    execution: dict[str, Any] = field(default_factory=lambda: {"steps": [], "tools": [], "trace": {}})
    outcome: dict[str, Any] = field(default_factory=lambda: {"success": False, "metrics": {}})
    reflection: dict[str, Any] = field(default_factory=lambda: {"what_worked": [], "what_failed": [], "why": ""})
    reusable_patterns: list[dict] = field(default_factory=list)
    confidence_score: float = 0.5
    provenance: dict[str, Any] = field(default_factory=lambda: {"human_signals": [], "agent_signals": [], "external_sources": []})
    version: int = 1
    visibility: str = "private"

    def to_api(self) -> dict:
        """转换为 API 请求体."""
        return {
            "context": self.context,
            "intent": self.intent,
            "execution": self.execution,
            "outcome": self.outcome,
            "reflection": self.reflection,
            "reusable_patterns": self.reusable_patterns,
            "confidence_score": self.confidence_score,
            "provenance": self.provenance,
            "version": self.version,
            "visibility": self.visibility,
        }
