"""Aevum SDK 演示 - Agent 经验记忆闭环.

演示场景：一个简单的 Agent 执行"部署应用"任务。

第一次执行：
  1. 检索经验 -> 无相关经验（空库或新领域）
  2. 执行任务 -> 成功/失败
  3. 自动沉淀经验

第二次执行（相似任务）：
  1. 检索经验 -> 找到上次的经验
  2. 参考经验 -> 跳过已知的坑
  3. 执行任务 -> 更快更好
  4. 自动沉淀改进后的经验

Usage:
    cd backend
    python -m sdk.demo --api-key your-agent-key

    或在 Docker 中:
    docker exec aevum-backend python -m sdk.demo --api-key your-agent-key
"""

import argparse
import sys
import time

from aevum import AevumClient


def simulate_agent_execution(task: str, has_experience: bool) -> dict:
    """模拟 Agent 执行任务.

    真实场景中，这里会调用你的 Agent 框架（AutoGPT/CrewAI/LangGraph）。
    演示用：模拟执行结果。
    """
    print(f"\n  [Agent] 执行任务: {task}")

    if has_experience:
        # 有经验参考 -> 更快更好
        print("  [Agent] 参考历史经验，跳过已知坑...")
        time.sleep(0.3)  # 模拟快速执行
        return {
            "success": True,
            "what_worked": ["docker build -t app .", "docker run -d app"],
            "what_failed": [],
            "why": "参考历史经验，直接使用验证过的部署流程",
            "tools": ["docker"],
            "metrics": {"duration_s": 12},
            "confidence": 0.9,
        }
    else:
        # 无经验 -> 慢且可能踩坑
        print("  [Agent] 无历史经验，从零开始试错...")
        time.sleep(0.8)  # 模拟缓慢执行
        return {
            "success": True,
            "what_worked": ["docker build -t app ."],
            "what_failed": ["docker run app（缺少 -d 参数，前台阻塞）"],
            "why": "首次执行，试错发现需要 -d 参数后台运行",
            "tools": ["docker"],
            "metrics": {"duration_s": 45},
            "confidence": 0.6,
        }


def run_first_time(client: AevumClient) -> None:
    """第一次执行：无经验参考."""
    print("\n" + "=" * 60)
    print("场景 1: 首次执行（无经验参考）")
    print("=" * 60)

    task = "用 Docker 部署 Python Flask 应用"

    with client.memory(
        task=task,
        domain="devops",
        task_type="deployment",
        constraints={"env": "production"},
        visibility="public",
    ) as mem:
        # 检索阶段
        print(f"\n  [检索] 搜索相似经验: '{task}'")
        if mem.relevant_experiences:
            for r in mem.relevant_experiences:
                print(f"    - [{r.similarity:.0%}] {r.intent}")
        else:
            print("    (无相关经验)")

        # 执行阶段
        result = simulate_agent_execution(task, has_experience=bool(mem.relevant_experiences))

        # 记录结果
        mem.record_outcome(
            success=result["success"],
            what_worked=result["what_worked"],
            what_failed=result["what_failed"],
            why=result["why"],
            tools=result["tools"],
            metrics=result["metrics"],
            confidence=result["confidence"],
        )

    print(f"\n  [沉淀] 经验已自动存储 (visibility=public)")
    print(f"  耗时: {result['metrics']['duration_s']}s | 置信度: {result['confidence']}")


def run_second_time(client: AevumClient) -> None:
    """第二次执行：有经验参考."""
    print("\n" + "=" * 60)
    print("场景 2: 第二次执行（有经验参考）")
    print("=" * 60)

    task = "用 Docker 部署 Python FastAPI 应用"  # 相似但不同的任务

    with client.memory(
        task=task,
        domain="devops",
        task_type="deployment",
        constraints={"env": "production"},
        visibility="public",
    ) as mem:
        # 检索阶段
        print(f"\n  [检索] 搜索相似经验: '{task}'")
        if mem.relevant_experiences:
            print(f"    找到 {len(mem.relevant_experiences)} 条相关经验:")
            for r in mem.relevant_experiences:
                print(f"\n{r.summary()}")
        else:
            print("    (无相关经验)")

        # 执行阶段 - 这次有经验参考
        result = simulate_agent_execution(task, has_experience=bool(mem.relevant_experiences))

        # 记录结果
        mem.record_outcome(
            success=result["success"],
            what_worked=result["what_worked"],
            what_failed=result["what_failed"],
            why=result["why"],
            tools=result["tools"],
            metrics=result["metrics"],
            confidence=result["confidence"],
        )

    print(f"\n  [沉淀] 改进后的经验已自动存储")
    print(f"  耗时: {result['metrics']['duration_s']}s | 置信度: {result['confidence']}")

    # 对比
    if mem.relevant_experiences:
        print("\n" + "-" * 60)
        print("对比:")
        print(f"  首次执行: 45s (试错, 置信度 0.6)")
        print(f"  二次执行: {result['metrics']['duration_s']}s (有经验参考, 置信度 {result['confidence']})")
        print(f"  效率提升: {((45 - result['metrics']['duration_s']) / 45 * 100):.0f}%")
        print("-" * 60)


def run_manual_api_demo(client: AevumClient) -> None:
    """手动 API 调用演示（不使用 memory 上下文）."""
    print("\n" + "=" * 60)
    print("场景 3: 手动 API 调用")
    print("=" * 60)

    # 检索
    print("\n  [search] 检索 Docker 相关经验...")
    results = client.search("Docker deployment", domain="devops", limit=3)
    print(f"    找到 {len(results)} 条经验")
    for r in results:
        print(f"    - [{r.similarity:.0%}] {r.intent}")

    # 手动存储
    print("\n  [create_experience] 手动存储一条经验...")
    exp = client.create_experience(
        context={"domain": "testing", "task_type": "unit_test", "constraints": {}},
        intent="运行 pytest 并生成覆盖率报告",
        outcome={"success": True, "metrics": {"coverage": 0.85}},
        execution={"steps": [{"action": "run", "cmd": "pytest --cov"}], "tools": ["pytest"], "trace": {}},
        reflection={"what_worked": ["pytest --cov=app"], "what_failed": [], "why": "标准流程"},
        confidence_score=0.8,
        visibility="public",
    )
    print(f"    经验已存储, id={exp.get('id', 'N/A')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Aevum SDK 演示")
    parser.add_argument("--api-key", required=True, help="Agent API Key")
    parser.add_argument("--base-url", default="http://localhost:8000", help="服务地址")
    args = parser.parse_args()

    print("=" * 60)
    print("Aevum SDK 演示 - Agent 经验记忆闭环")
    print("=" * 60)
    print(f"  服务地址: {args.base_url}")
    print(f"  API Key: {args.api_key[:8]}...")

    with AevumClient(api_key=args.api_key, base_url=args.base_url) as client:
        # 场景 1: 首次执行
        run_first_time(client)

        # 场景 2: 二次执行（复用经验）
        run_second_time(client)

        # 场景 3: 手动 API
        run_manual_api_demo(client)

    print("\n" + "=" * 60)
    print("演示完成!")
    print("=" * 60)
    print("\n核心价值:")
    print("  - Agent 执行前自动检索经验，跳过试错")
    print("  - 执行后自动沉淀经验，形成复利")
    print("  - 使用越多，经验越丰富，执行越快")
    print("\n接入你的 Agent:")
    print("  from aevum import AevumClient")
    print("  client = AevumClient(api_key='your-key')")
    print("  with client.memory('your task') as mem:")
    print("      result = your_agent.execute(...)")
    print("      mem.record_outcome(success=True, ...)")


if __name__ == "__main__":
    sys.exit(main())
