"""端到端集成测试 - 验证完整8步流水线闭环.

测试流程:
1. 提交任务 (POST /execution/tasks)
2. 验证8步流水线全部完成
3. 验证经验已入库 (GET /experiences/{id})
4. 评估经验 (POST /evaluation/experiences/{id})
5. 验证经验可被检索 (POST /retrieval/search)
6. 验证Dashboard数据更新 (GET /evaluation/dashboard)
"""

import asyncio
import sys
import httpx
import json

API_BASE = "http://localhost:8000/api/v1"


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def pass_msg(msg: str):
    print(f"  {Colors.GREEN}[PASS]{Colors.RESET} {msg}")

def fail_msg(msg: str):
    print(f"  {Colors.RED}[FAIL]{Colors.RESET} {msg}")

def info_msg(msg: str):
    print(f"  {Colors.CYAN}[INFO]{Colors.RESET} {msg}")

def step_msg(msg: str):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}>>> {msg}{Colors.RESET}")


async def run_e2e_test():
    """运行端到端测试."""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  薪火 OS - 端到端集成测试{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

    passed = 0
    failed = 0
    experience_id = None

    async with httpx.AsyncClient(base_url=API_BASE, timeout=30) as client:
        # ── Step 0: 健康检查 ──
        step_msg("Step 0: 后端健康检查")
        r = await client.get("http://localhost:8000/health")
        if r.status_code == 200 and r.json().get("status") == "ok":
            pass_msg("后端服务正常")
            passed += 1
        else:
            fail_msg(f"健康检查失败: {r.status_code}")
            failed += 1
            return

        # ── Step 1: 提交任务 ──
        step_msg("Step 1: 提交任务 (触发8步流水线)")
        task_body = {
            "intent": "E2E test: optimize database query performance with indexing",
            "context": {
                "domain": "backend",
                "task_type": "optimization",
                "constraints": {"env": "testing", "timeout": 30, "resource_limit": "low"}
            }
        }
        r = await client.post("/execution/tasks", json=task_body)
        if r.status_code in (200, 201, 202):
            task_data = r.json()
            task_id = task_data.get("id")
            experience_id = task_data.get("experience_id")
            info_msg(f"Task ID: {task_id}")
            info_msg(f"Experience ID: {experience_id}")
            info_msg(f"Status: {task_data.get('status')}")
            pass_msg("任务提交成功")
            passed += 1
        else:
            fail_msg(f"任务提交失败: {r.status_code} {r.text}")
            failed += 1
            return

        # ── Step 2: 验证8步流水线 ──
        step_msg("Step 2: 验证8步流水线全部完成")
        pipeline_state = task_data.get("pipeline_state", {})
        all_completed = True
        for step_num in range(1, 9):
            step = pipeline_state.get(str(step_num), {})
            status = step.get("status")
            name = step.get("name", f"step_{step_num}")
            if status == "completed":
                pass_msg(f"Step {step_num}: {name} - completed")
            else:
                fail_msg(f"Step {step_num}: {name} - {status}")
                all_completed = False

        if all_completed:
            pass_msg("8步流水线全部完成")
            passed += 1
        else:
            fail_msg("流水线有未完成的步骤")
            failed += 1

        # ── Step 3: 验证经验已入库 ──
        step_msg("Step 3: 验证经验已入库")
        if not experience_id:
            fail_msg("未获取到 experience_id")
            failed += 1
        else:
            r = await client.get(f"/experiences/{experience_id}")
            if r.status_code == 200:
                exp = r.json()
                info_msg(f"Intent: {exp.get('intent')}")
                info_msg(f"Domain: {exp.get('context', {}).get('domain')}")
                info_msg(f"Success: {exp.get('outcome', {}).get('success')}")
                info_msg(f"Confidence: {exp.get('confidence_score')}")
                info_msg(f"Eval Status: {exp.get('evaluation_status')}")
                pass_msg("经验已入库")
                passed += 1
            else:
                fail_msg(f"获取经验失败: {r.status_code}")
                failed += 1

        # ── Step 4: 评估经验 ──
        step_msg("Step 4: 评估经验")
        if experience_id:
            r = await client.post(f"/evaluation/experiences/{experience_id}")
            if r.status_code == 200:
                eval_data = r.json()
                info_msg(f"Overall Score: {eval_data.get('overall_score')}")
                info_msg(f"Confidence: {eval_data.get('confidence_score')}")
                info_msg(f"Summary: {eval_data.get('summary')}")
                pass_msg("经验评估成功")
                passed += 1
            else:
                fail_msg(f"评估失败: {r.status_code} {r.text}")
                failed += 1

        # ── Step 5: 验证经验可被检索 ──
        step_msg("Step 5: 验证检索系统")
        search_body = {
            "query": "database query performance optimization indexing",
            "limit": 10
        }
        r = await client.post("/retrieval/search", json=search_body)
        if r.status_code == 200:
            search_results = r.json()
            info_msg(f"检索返回 {len(search_results)} 条结果")
            for i, result in enumerate(search_results[:3]):
                info_msg(f"  #{i+1} Score: {result.get('score', 0):.4f} | {result.get('experience', {}).get('intent', 'N/A')}")
            pass_msg("检索系统正常工作")
            passed += 1
        else:
            fail_msg(f"检索失败: {r.status_code}")
            failed += 1

        # ── Step 6: 验证Dashboard数据 ──
        step_msg("Step 6: 验证Dashboard数据")
        r = await client.get("/evaluation/dashboard")
        if r.status_code == 200:
            dashboard = r.json()
            stats = dashboard.get("experience_stats", {})
            metrics = dashboard.get("system_metrics", {})
            info_msg(f"Total: {stats.get('total')}")
            info_msg(f"Evaluated: {stats.get('evaluated')}")
            info_msg(f"Pending: {stats.get('pending')}")
            info_msg(f"Avg Confidence: {stats.get('avg_confidence')}")
            info_msg(f"Reuse Rate: {metrics.get('experience_reuse_rate', 0):.1%}")
            info_msg(f"Success Rate: {metrics.get('workflow_success_rate', 0):.1%}")
            pass_msg("Dashboard数据正常")
            passed += 1
        else:
            fail_msg(f"Dashboard获取失败: {r.status_code}")
            failed += 1

        # ── Step 7: 验证经验列表 ──
        step_msg("Step 7: 验证经验列表API")
        r = await client.get("/experiences", params={"page": 1, "page_size": 5})
        if r.status_code == 200:
            list_data = r.json()
            info_msg(f"Total: {list_data.get('total')}")
            info_msg(f"Page items: {len(list_data.get('items', []))}")
            pass_msg("经验列表API正常")
            passed += 1
        else:
            fail_msg(f"经验列表获取失败: {r.status_code}")
            failed += 1

    # ── 结果汇总 ──
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  测试结果: {Colors.GREEN}{passed} passed{Colors.RESET}", end="")
    if failed > 0:
        print(f", {Colors.RED}{failed} failed{Colors.RESET}")
    else:
        print(f", {failed} failed")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_e2e_test())
    sys.exit(0 if success else 1)
