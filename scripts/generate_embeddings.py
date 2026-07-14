"""为所有经验生成 embedding 向量."""

import asyncio

from sqlalchemy import select, update
from sqlalchemy import text as sql_text

from app.core.database import async_session_factory, engine
from app.models.experience import Experience
from app.services.retrieval.embedder import HashEmbedder


async def generate_embeddings():
    embedder = HashEmbedder(dim=1536)
    updated = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(Experience.id, Experience.intent, Experience.context)
        )
        rows = result.all()
        total = len(rows)
        print(f"Found {total} experiences to embed")

        for i, (exp_id, intent, context) in enumerate(rows):
            # 构造用于 embedding 的文本
            domain = context.get("domain", "") if context else ""
            task_type = context.get("task_type", "") if context else ""
            embed_text = f"{domain} {task_type} {intent}"

            vector = embedder.embed(embed_text)

            # 直接使用 raw SQL 更新 pgvector 列
            vector_str = f"[{','.join(str(v) for v in vector)}]"
            await session.execute(
                sql_text("UPDATE experiences SET embedding = :vec WHERE id = :id"),
                {"vec": vector_str, "id": str(exp_id)},
            )

            updated += 1
            if (i + 1) % 100 == 0:
                await session.commit()
                print(f"  Embedded {i + 1}/{total}...")

        await session.commit()

    print(f"\nDone: {updated} embeddings generated")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(generate_embeddings())
