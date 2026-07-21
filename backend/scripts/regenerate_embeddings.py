"""重新生成所有经验的 embedding（使用火山引擎 doubao-embedding-vision）."""
import asyncio
import sys

import httpx
from sqlalchemy import text

from app.core.config import settings
from app.core.database import async_session_factory

BASE_URL = settings.openai_base_url.rstrip("/")
API_KEY = settings.openai_api_key
MODEL = settings.embedding_model
DIM = settings.embedding_dimension
BATCH_SIZE = 20
CONCURRENCY = 2
RETRY_MAX = 3
RETRY_WAIT = 2  # 秒


async def embed_one(client: httpx.AsyncClient, sem: asyncio.Semaphore, exp_id: str, intent: str, domain: str, task_type: str) -> tuple[str, list[float]]:
    embed_text = f"{intent} {domain} {task_type}"
    async with sem:
        for attempt in range(RETRY_MAX):
            try:
                payload: dict = {"input": embed_text, "model": MODEL}
                if DIM and DIM < 2048:
                    payload["dimensions"] = DIM
                r = await client.post(
                    f"{BASE_URL}/embeddings",
                    headers={"Authorization": f"Bearer {API_KEY}"},
                    json=payload,
                )
                if r.status_code == 429:
                    wait = RETRY_WAIT * (attempt + 1) * 2
                    print(f"  ⏳ 429限流, 等待{wait}秒后重试...")
                    await asyncio.sleep(wait)
                    continue
                r.raise_for_status()
                return exp_id, r.json()["data"][0]["embedding"]
            except Exception as e:
                if attempt < RETRY_MAX - 1:
                    await asyncio.sleep(RETRY_WAIT)
                    continue
                print(f"  ❌ {str(exp_id)[:8]}: {e}")
                return exp_id, []
        return exp_id, []


async def main():
    print(f"模型: {MODEL}, 维度: {DIM}")
    print(f"API: {BASE_URL}/embeddings")

    async with async_session_factory() as session:
        result = await session.execute(text("SELECT count(*) FROM experiences WHERE embedding IS NULL"))
        total = result.scalar()
        print(f"待重新生成 embedding 的经验: {total}")

        if total == 0:
            print("✅ 所有经验已有 embedding，无需重新生成")
            return

        sem = asyncio.Semaphore(CONCURRENCY)
        processed = 0
        failed = 0

        async with httpx.AsyncClient(timeout=60) as client:
            offset = 0
            while offset < total:
                result = await session.execute(
                    text(
                        "SELECT id, intent, context->>'domain' as domain, context->>'task_type' as task_type "
                        "FROM experiences WHERE embedding IS NULL LIMIT :limit"
                    ),
                    {"limit": BATCH_SIZE},
                )
                batch = result.fetchall()
                if not batch:
                    break

                tasks = [
                    embed_one(client, sem, row.id, row.intent or "", row.domain or "", row.task_type or "")
                    for row in batch
                ]
                results = await asyncio.gather(*tasks)

                for exp_id, emb in results:
                    if emb:
                        await session.execute(
                            text("UPDATE experiences SET embedding = :emb WHERE id = :id"),
                            {"emb": str(emb), "id": exp_id},
                        )
                    else:
                        failed += 1

                await session.commit()
                processed += len(batch)
                print(f"  进度: {processed}/{total} ({processed*100//total}%)")
                offset += BATCH_SIZE

        print(f"\n✅ 完成: {processed - failed} 成功, {failed} 失败")


if __name__ == "__main__":
    asyncio.run(main())
