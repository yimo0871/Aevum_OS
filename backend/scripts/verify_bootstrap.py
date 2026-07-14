"""Bootstrap verification - 冷启动验证.

验证种子数据的质量和系统功能：
1. 检索精度：种子经验可被正确检索
2. 评估覆盖率：所有种子经验有评估结果
3. 图谱连通性：经验间有关系

Usage:
    python scripts/verify_bootstrap.py --api http://localhost:8000
    python scripts/verify_bootstrap.py --seeds seeds.json
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path


async def verify_via_api(api_url: str) -> None:
    """Verify bootstrap via API."""
    import httpx

    print("=" * 60)
    print("Aevum OS - Bootstrap Verification")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        # ── 1. Health Check ──
        print("\n1. Health Check")
        try:
            response = await client.get(f"{api_url}/health")
            if response.status_code == 200:
                print("   ✅ Backend is healthy")
            else:
                print(f"   ❌ Backend health check failed: {response.status_code}")
                return
        except Exception as e:
            print(f"   ❌ Cannot connect to backend: {e}")
            return

        # ── 2. Experience Count ──
        print("\n2. Experience Count")
        response = await client.get(f"{api_url}/api/v1/experiences?page=1&page_size=1")
        if response.status_code == 200:
            data = response.json()
            total = data.get("total", 0)
            print(f"   Total experiences: {total}")
            if total >= 10000:
                print("   ✅ Bootstrap target (10,000) reached")
            elif total > 0:
                print(f"   ⚠️  Bootstrap target not reached: {total}/10000")
            else:
                print("   ❌ No experiences found. Run bootstrap_seeds.py first.")
        else:
            print(f"   ❌ Failed to get experiences: {response.status_code}")

        # ── 3. Domain Distribution ──
        print("\n3. Domain Distribution")
        domains = ["devops", "frontend", "backend", "data", "testing", "security", "ml", "general"]
        for domain in domains:
            response = await client.get(f"{api_url}/api/v1/experiences?domain={domain}&page=1&page_size=1")
            if response.status_code == 200:
                count = response.json().get("total", 0)
                print(f"   {domain}: {count}")

        # ── 4. Evaluation Coverage ──
        print("\n4. Evaluation Coverage")
        response = await client.get(f"{api_url}/api/v1/evaluation/dashboard")
        if response.status_code == 200:
            data = response.json()
            stats = data.get("experience_stats", {})
            total = stats.get("total", 0)
            evaluated = stats.get("evaluated", 0)
            pending = stats.get("pending", 0)
            coverage = (evaluated / total * 100) if total > 0 else 0
            print(f"   Total: {total}")
            print(f"   Evaluated: {evaluated} ({coverage:.1f}%)")
            print(f"   Pending: {pending}")
            if coverage >= 80:
                print("   ✅ Evaluation coverage >= 80%")
            else:
                print(f"   ⚠️  Evaluation coverage {coverage:.1f}% < 80%")

        # ── 5. System Metrics ──
        print("\n5. System Metrics")
        response = await client.get(f"{api_url}/api/v1/evaluation/metrics")
        if response.status_code == 200:
            metrics = response.json().get("metrics", {})
            for key, value in metrics.items():
                print(f"   {key}: {value:.4f}")

        # ── 6. Search Test ──
        print("\n6. Search Test")
        test_queries = [
            "deploy application to production",
            "write unit tests",
            "train machine learning model",
        ]
        for query in test_queries:
            response = await client.post(
                f"{api_url}/api/v1/retrieval/search",
                json={"query": query, "limit": 3},
            )
            if response.status_code == 200:
                results = response.json()
                print(f"   Query: '{query}' -> {len(results)} results")
                if results:
                    top = results[0]
                    print(f"     Top score: {top.get('score', 0):.4f}")
            else:
                print(f"   Query: '{query}' -> Error: {response.status_code}")

        # ── 7. Available Tools ──
        print("\n7. Available Tools")
        response = await client.get(f"{api_url}/api/v1/execution/tools")
        if response.status_code == 200:
            tools = response.json()
            print(f"   Registered tools: {len(tools)}")
            for tool in tools:
                print(f"     - {tool['name']}: {tool['description']}")

    print("\n" + "=" * 60)
    print("Verification complete.")
    print("=" * 60)


def verify_seeds_file(seeds_path: str) -> None:
    """Verify seed data from JSON file."""
    print("=" * 60)
    print("Aevum OS - Seed Data Verification")
    print("=" * 60)

    with open(seeds_path, encoding="utf-8") as f:
        data = json.load(f)

    experiences = data.get("experiences", [])
    relations = data.get("relations", [])

    print(f"\n1. Data Volume")
    print(f"   Experiences: {len(experiences)}")
    print(f"   Relations: {len(relations)}")

    if len(experiences) >= 10000:
        print("   ✅ Bootstrap target (10,000) reached")
    else:
        print(f"   ⚠️  Only {len(experiences)} experiences (target: 10,000)")

    # Domain distribution
    print(f"\n2. Domain Distribution")
    domain_counts: dict[str, int] = {}
    for exp in experiences:
        d = exp["context"]["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
    for d, c in sorted(domain_counts.items(), key=lambda x: -x[1]):
        print(f"   {d}: {c} ({c/len(experiences)*100:.1f}%)")

    # Success rate
    print(f"\n3. Success Rate")
    success_count = sum(1 for e in experiences if e["outcome"]["success"])
    print(f"   Success: {success_count} ({success_count/len(experiences)*100:.1f}%)")
    print(f"   Failed: {len(experiences) - success_count} ({(len(experiences) - success_count)/len(experiences)*100:.1f}%)")

    # Confidence distribution
    print(f"\n4. Confidence Distribution")
    scores = [e["confidence_score"] for e in experiences]
    avg = sum(scores) / len(scores)
    print(f"   Average: {avg:.4f}")
    print(f"   Min: {min(scores):.4f}")
    print(f"   Max: {max(scores):.4f}")

    # Graph connectivity
    print(f"\n5. Graph Connectivity")
    source_ids = {r["source_id"] for r in relations}
    target_ids = {r["target_id"] for r in relations}
    connected = source_ids | target_ids
    print(f"   Unique relations: {len(relations)}")
    print(f"   Connected experiences: {len(connected)}")
    print(f"   Connectivity: {len(connected)/len(experiences)*100:.1f}%")

    relation_types: dict[str, int] = {}
    for r in relations:
        rt = r["relation_type"]
        relation_types[rt] = relation_types.get(rt, 0) + 1
    print(f"   Relation types:")
    for rt, c in sorted(relation_types.items(), key=lambda x: -x[1]):
        print(f"     {rt}: {c}")

    print("\n" + "=" * 60)
    print("Seed data verification complete.")
    print("=" * 60)


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Aevum OS bootstrap data")
    parser.add_argument("--api", type=str, help="API URL for live verification")
    parser.add_argument("--seeds", type=str, help="Path to seeds JSON file")

    args = parser.parse_args()

    if args.api:
        asyncio.run(verify_via_api(args.api))
    elif args.seeds:
        verify_seeds_file(args.seeds)
    else:
        # Try default seeds file
        default_path = Path("seeds.json")
        if default_path.exists():
            verify_seeds_file(str(default_path))
        else:
            parser.print_help()
            print("\nError: No --api or --seeds specified, and seeds.json not found.")


if __name__ == "__main__":
    main()
