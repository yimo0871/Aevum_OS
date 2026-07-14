"""调试检索功能."""
import asyncio
from app.services.retrieval.matcher import ExperienceMatcher
from app.core.database import async_session_factory, engine

async def test():
    async with async_session_factory() as session:
        m = ExperienceMatcher(session)
        try:
            results = await m.match_by_vector("后端开发 API认证", limit=5)
            print(f"vector results: {len(results)}")
            for r in results[:3]:
                dom = r.experience.context.get("domain", "")
                print(f"  sim={r.similarity:.4f} domain={dom}")
        except Exception as e:
            print(f"vector error: {type(e).__name__}: {e}")

        try:
            results2 = await m.match_by_keywords("后端开发", limit=5)
            print(f"keyword results: {len(results2)}")
            for r in results2[:3]:
                dom = r.experience.context.get("domain", "")
                print(f"  score={r.similarity:.4f} domain={dom}")
        except Exception as e:
            print(f"keyword error: {type(e).__name__}: {e}")

    await engine.dispose()

asyncio.run(test())
