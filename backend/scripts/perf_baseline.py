"""性能基线压测脚本.

测量 API 关键端点的 P50/P95/P99 延迟和 QPS。
用法: docker exec aevum-backend python scripts/perf_baseline.py
"""

import asyncio
import statistics
import time

import httpx

BASE_URL = "http://localhost:8000"
CONCURRENT = 10
TOTAL_REQUESTS = 100


async def measure_endpoint(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    json_body: dict | None = None,
    label: str = "",
) -> dict:
    """测量单个端点的性能."""
    latencies: list[float] = []
    errors = 0

    async def single_request():
        nonlocal errors
        try:
            start = time.perf_counter()
            if method == "GET":
                resp = await client.get(f"{BASE_URL}{path}", timeout=10)
            else:
                resp = await client.post(f"{BASE_URL}{path}", json=json_body, timeout=10)
            elapsed = (time.perf_counter() - start) * 1000  # ms
            latencies.append(elapsed)
            if resp.status_code >= 400:
                errors += 1
        except Exception:
            errors += 1

    # 并发执行
    sem = asyncio.Semaphore(CONCURRENT)

    async def bounded():
        async with sem:
            await single_request()

    tasks = [bounded() for _ in range(TOTAL_REQUESTS)]
    start_time = time.perf_counter()
    await asyncio.gather(*tasks)
    total_time = time.perf_counter() - start_time

    latencies.sort()
    return {
        "label": label,
        "requests": TOTAL_REQUESTS,
        "errors": errors,
        "qps": round(TOTAL_REQUESTS / total_time, 1),
        "p50_ms": round(statistics.median(latencies), 1) if latencies else 0,
        "p95_ms": round(latencies[int(len(latencies) * 0.95)], 1) if latencies else 0,
        "p99_ms": round(latencies[int(len(latencies) * 0.99)], 1) if latencies else 0,
    }


async def main():
    """运行性能基线测试."""
    print("=" * 60)
    print("Aevum 性能基线压测")
    print(f"并发: {CONCURRENT}, 总请求: {TOTAL_REQUESTS}")
    print("=" * 60)

    async with httpx.AsyncClient() as client:
        # 健康检查
        result = await measure_endpoint(
            client, "GET", "/health", label="GET /health"
        )
        print(f"\n{result['label']}:")
        print(
            f"  QPS: {result['qps']} | P50: {result['p50_ms']}ms | "
            f"P95: {result['p95_ms']}ms | P99: {result['p99_ms']}ms | Errors: {result['errors']}"
        )

        # 检索搜索
        result = await measure_endpoint(
            client,
            "POST",
            "/api/v1/retrieval/search",
            json_body={"query": "deploy python app", "limit": 5},
            label="POST /api/v1/retrieval/search",
        )
        print(f"\n{result['label']}:")
        print(
            f"  QPS: {result['qps']} | P50: {result['p50_ms']}ms | "
            f"P95: {result['p95_ms']}ms | P99: {result['p99_ms']}ms | Errors: {result['errors']}"
        )

        # 经验列表
        result = await measure_endpoint(
            client,
            "GET",
            "/api/v1/experiences?page=1&page_size=10",
            label="GET /api/v1/experiences",
        )
        print(f"\n{result['label']}:")
        print(
            f"  QPS: {result['qps']} | P50: {result['p50_ms']}ms | "
            f"P95: {result['p95_ms']}ms | P99: {result['p99_ms']}ms | Errors: {result['errors']}"
        )

    print("\n" + "=" * 60)
    print("压测完成")


if __name__ == "__main__":
    asyncio.run(main())
