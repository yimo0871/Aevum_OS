"""API 压力测试 - 验证 100 并发 P95 < 1s."""
import asyncio
import time
import statistics
import httpx

API_BASE = "http://localhost:8000"

async def hit_endpoint(client, url, method="GET", json=None):
    """单次请求，返回耗时(ms)."""
    start = time.perf_counter()
    try:
        if method == "GET":
            resp = await client.get(url)
            await resp.aread()
            status = resp.status_code
        else:
            resp = await client.post(url, json=json)
            await resp.aread()
            status = resp.status_code
    except Exception:
        status = 0
    elapsed = (time.perf_counter() - start) * 1000
    return elapsed, status


async def run_concurrent(url, method="GET", json=None, concurrency=100, total=200):
    """并发压测."""
    latencies = []
    errors = 0

    async with httpx.AsyncClient() as client:
        # 预热
        for _ in range(5):
            await hit_endpoint(client, url, method, json)

        # 正式测试
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request():
            nonlocal errors
            async with semaphore:
                lat, status = await hit_endpoint(client, url, method, json)
                latencies.append(lat)
                if status >= 400:
                    errors += 1

        tasks = [bounded_request() for _ in range(total)]
        await asyncio.gather(*tasks)

    latencies.sort()
    return {
        "total": len(latencies),
        "errors": errors,
        "min_ms": round(latencies[0], 1),
        "avg_ms": round(statistics.mean(latencies), 1),
        "p50_ms": round(latencies[len(latencies) // 2], 1),
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1),
        "p99_ms": round(latencies[int(len(latencies) * 0.99)], 1),
        "max_ms": round(latencies[-1], 1),
    }


async def main():
    print("=" * 60)
    print("API 压力测试 - 100 并发, P95 < 1000ms")
    print("=" * 60)

    tests = [
        ("健康检查", f"{API_BASE}/health", "GET", None),
        ("经验列表", f"{API_BASE}/api/v1/experiences?page=1&page_size=20", "GET", None),
        ("Dashboard", f"{API_BASE}/api/v1/evaluation/dashboard", "GET", None),
        ("向量检索", f"{API_BASE}/api/v1/retrieval/search", "POST",
         {"query": "后端开发 API认证", "limit": 10}),
    ]

    results = {}
    for name, url, method, json_data in tests:
        print(f"\n>>> {name} ({method} {url.split(':8000')[1]})")
        r = await run_concurrent(url, method, json_data, concurrency=100, total=200)
        results[name] = r
        status = "PASS" if r["p95_ms"] < 1000 and r["errors"] == 0 else "FAIL"
        print(f"    {status} | P50: {r['p50_ms']:.0f}ms | P95: {r['p95_ms']:.0f}ms | "
              f"错误: {r['errors']}/{r['total']}")

    print("\n" + "=" * 60)
    print("压测总结:")
    all_pass = True
    for name, r in results.items():
        ok = r["p95_ms"] < 1000 and r["errors"] == 0
        if not ok:
            all_pass = False
        print(f"  {'PASS' if ok else 'FAIL'} {name}: P95={r['p95_ms']:.0f}ms, "
              f"errors={r['errors']}/{r['total']}")

    print(f"\n{'ALL PASS' if all_pass else 'SOME FAILED'}")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
