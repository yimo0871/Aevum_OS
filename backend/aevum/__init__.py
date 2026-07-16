"""Aevum SDK - Agent 经验记忆层.

让任何 Agent 框架接入 Aevum 作为经验后端，实现：
- 执行前检索相似经验（跳过试错）
- 执行后自动沉淀经验（复利积累）

Usage:
    from aevum import AevumClient

    client = AevumClient(api_key="your-key", base_url="http://localhost:8000")

    # 检索经验
    results = client.search("deploy React to Vercel", domain="frontend")

    # 存储经验
    client.create_experience(
        context={"domain": "frontend", "task_type": "deployment"},
        intent="deploy React to Vercel",
        outcome={"success": True, "metrics": {}},
    )

    # 高级：自动记忆上下文
    with client.memory("deploy React to Vercel", domain="frontend") as mem:
        result = your_agent.execute(...)
        mem.record_outcome(success=True, what_worked=["vercel deploy --prod"])
"""

from aevum.client import AevumClient
from aevum.models import Experience, SearchResult

__version__ = "0.1.0"
__all__ = ["AevumClient", "Experience", "SearchResult"]
