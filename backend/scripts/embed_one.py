"""为单条经验生成 embedding."""

import asyncio
import sys

from sqlalchemy import select, text

from app.core.database import async_session_factory, engine
from app.models.experience import Experience
from app.services.retrieval.embedder import HashEmbedder


async def embed_one(exp_id: str):
    embedder = HashEmbedder(dim=1536)

    async with async_session_factory() as session:
        result = await session.execute(
            select(Experience.id, Experience.intent, Experience.context).where(
                Experience.id == exp_id
            )
        )
        row = result.first()
        if not row:
            print(f"Experience {exp_id} not found")
            return

        domain = row[2].get("domain", "") if row[2] else ""
        task_type = row[2].get("task_type", "") if row[2] else ""
        embed_text = f"{domain} {task_type} {row[1]}"

        vector = embedder.embed(embed_text)
        vector_str = f"[{','.join(str(v) for v in vector)}]"

        await session.execute(
            text("UPDATE experiences SET embedding = :vec WHERE id = :id"),
            {"vec": vector_str, "id": str(row[0])},
        )
        await session.commit()
        print(f"Embedding generated for {exp_id}")

    await engine.dispose()


if __name__ == "__main__":
    exp_id = sys.argv[1] if len(sys.argv) > 1 else ""
    if not exp_id:
        print("Usage: python embed_one.py <experience_id>")
        sys.exit(1)
    asyncio.run(embed_one(exp_id))
