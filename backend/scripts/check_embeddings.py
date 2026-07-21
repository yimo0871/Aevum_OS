"""检查新创建经验是否有 embedding."""
import asyncio
from sqlalchemy import text
from app.core.database import async_session_factory

async def check():
    async with async_session_factory() as session:
        # 检查最近创建的5条经验
        result = await session.execute(
            text("SELECT id, intent, embedding IS NOT NULL as has_emb FROM experiences ORDER BY created_at DESC LIMIT 5")
        )
        rows = result.fetchall()
        print("最近5条经验:")
        for r in rows:
            print(f"  id={str(r.id)[:8]} has_emb={r.has_emb} intent={r.intent[:40]}")

        # 统计有/无embedding的数量
        result2 = await session.execute(
            text("SELECT count(*) FILTER (WHERE embedding IS NOT NULL) as with_emb, count(*) FILTER (WHERE embedding IS NULL) as without_emb FROM experiences")
        )
        stats = result2.fetchone()
        print(f"\n总计: 有embedding={stats.with_emb}, 无embedding={stats.without_emb}")

asyncio.run(check())
