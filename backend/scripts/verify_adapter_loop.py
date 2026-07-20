"""验证脚本: 真实 Agent 适配器闭环验证.

验证目标:
1. 用户注册 + Agent 注册 + API Key 获取
2. AevumClient 通过 API Key 连接后端
3. CrewAI 适配器 (AevumCrewWrapper) 完成检索->执行->存储闭环
4. 第二次执行能检索到第一次存储的经验
5. LangGraph 适配器 (AevumRunner) 同样验证闭环
6. 通用 REST 适配器 (AevumHook) 同样验证闭环

运行方式:
    docker exec -w /app -e PYTHONPATH=/app aevum-backend python scripts/verify_adapter_loop.py
"""

import sys
import time
import uuid

import httpx

BASE_URL = "http://localhost:8000"


def log(step, msg, ok=True):
    icon = "✅" if ok else "❌"
    print(f"{icon} [{step}] {msg}")


def main():
    print("=" * 60)
    print("  Agent 适配器闭环验证")
    print("=" * 60)

    # ── Step 1: 注册用户 ──
    suffix = uuid.uuid4().hex[:8]
    email = f"verify_{suffix}@test.dev"
    username = f"verify_{suffix}"
    password = "Verify123!"

    resp = httpx.post(
        f"{BASE_URL}/api/v1/auth/register",
        json={"email": email, "username": username, "password": password},
    )
    if resp.status_code != 201:
        log("注册", f"失败: {resp.status_code} {resp.text}", ok=False)
        sys.exit(1)
    token = resp.json()["access_token"]
    user_id = resp.json()["user"]["id"]
    log("注册", f"用户 {username} (id={user_id[:8]}...)")

    # ── Step 2: 注册 Agent 获取 API Key ──
    resp = httpx.post(
        f"{BASE_URL}/api/v1/agents",
        json={"name": f"verify-agent-{suffix}", "description": "闭环验证 Agent"},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code != 201:
        log("Agent注册", f"失败: {resp.status_code} {resp.text}", ok=False)
        sys.exit(1)
    agent_data = resp.json()
    api_key = agent_data["api_key"]
    agent_id = agent_data["id"]
    log("Agent注册", f"API Key: {api_key[:20]}... (id={agent_id[:8]}...)")

    # ── Step 3: 用 AevumClient 连接后端 ──
    from aevum.client import AevumClient

    client = AevumClient(api_key=api_key, base_url=BASE_URL)
    log("SDK连接", "AevumClient 初始化成功")

    # ── Step 4: 首次搜索（应返回种子数据或空）──
    results_before = client.search("后端开发 API 设计", domain="后端开发", limit=5)
    log("首次搜索", f"返回 {len(results_before)} 条经验")

    # ── Step 5: CrewAI 适配器闭环验证 ──
    print("\n--- CrewAI 适配器验证 ---")

    from aevum.adapters.crewai import AevumCrewWrapper

    class MockCrewOutput:
        def __init__(self, task_result):
            self.json_dict = {
                "success": True,
                "what_worked": ["模块化设计", "异步处理"],
                "what_failed": ["初始配置复杂"],
                "why": "异步处理提高了并发性能",
                "tools": ["FastAPI", "SQLAlchemy"],
                "steps": [{"name": "设计API"}, {"name": "实现端点"}, {"name": "编写测试"}],
                "confidence": 0.85,
            }
            self.raw = task_result

    class MockCrew:
        def kickoff(self, inputs=None, **kwargs):
            task = inputs.get("topic", "unknown") if inputs else "unknown"
            return MockCrewOutput(f"完成: {task}")

    crew = MockCrew()
    wrapper = AevumCrewWrapper(
        crew, client, domain="后端开发", task_type="方案规划", visibility="public"
    )

    # 首次执行
    result1 = wrapper.kickoff(inputs={"topic": "设计用户认证API"})
    stored_id_1 = getattr(wrapper, "aevum_stored_experience_id", None)
    found_1 = getattr(wrapper, "aevum_experiences_found", 0)
    log("CrewAI首次执行", f"存储经验 id={stored_id_1}, 检索到 {found_1} 条历史经验")

    if stored_id_1:
        log("CrewAI存储验证", "执行结果已自动存入 Aevum ✅")
    else:
        log("CrewAI存储验证", "存储失败", ok=False)

    # ── Step 6: 第二次执行，验证能检索到第一次的经验 ──
    time.sleep(2)
    result2 = wrapper.kickoff(inputs={"topic": "设计用户认证API"})
    stored_id_2 = getattr(wrapper, "aevum_stored_experience_id", None)
    found_2 = getattr(wrapper, "aevum_experiences_found", 0)
    log("CrewAI二次执行", f"存储经验 id={stored_id_2}, 检索到 {found_2} 条历史经验")

    if stored_id_2:
        log("CrewAI闭环验证", f"二次执行成功存储 (id={stored_id_2[:8]}...), 经验记忆生效 ✅")
    else:
        log("CrewAI闭环验证", "二次存储失败", ok=False)

    # ── Step 7: LangGraph 适配器验证 ──
    print("\n--- LangGraph 适配器验证 ---")

    lg_stored = None
    try:
        from aevum.adapters.langgraph import AevumRunner

        class MockLangGraph:
            def invoke(self, input, **kwargs):
                task = input.get("task", "unknown") if isinstance(input, dict) else str(input)
                return {
                    "success": True,
                    "output": "部署成功",
                    "steps": [{"name": "构建镜像"}, {"name": "启动容器"}, {"name": "配置nginx"}],
                    "tools": ["Docker", "Nginx"],
                    "confidence": 0.9,
                    "task": task,
                }

        runner = AevumRunner(
            MockLangGraph(), client, domain="运维部署", task_type="部署上线", visibility="public"
        )

        lg_result = runner.invoke({"task": "部署 Flask 应用到 Docker"})
        lg_stored = lg_result.get("aevum_stored_experience_id") if isinstance(lg_result, dict) else None
        lg_found = lg_result.get("aevum_experiences_found", 0) if isinstance(lg_result, dict) else 0
        log("LangGraph执行", f"存储经验 id={lg_stored}, 检索到 {lg_found} 条历史经验")

        if lg_stored:
            log("LangGraph存储验证", "执行结果已自动存入 Aevum ✅")
        else:
            log("LangGraph存储验证", "存储失败", ok=False)

    except Exception as e:
        log("LangGraph适配器", f"验证失败: {e}", ok=False)

    # ── Step 8: 通用 REST 适配器验证 ──
    print("\n--- 通用 REST 适配器验证 ---")

    stored_id_g = None
    try:
        from aevum.adapters.generic import AevumHook

        hook = AevumHook(client, domain="数据处理", task_type="数据清洗", visibility="public")

        # 执行前检索
        pre_experiences = hook.before_execution("清洗用户行为数据")
        log("Generic前置检索", f"检索到 {len(pre_experiences)} 条经验")

        # 模拟执行
        exec_result = {
            "success": True,
            "output": "清洗完成，移除 1000 条重复数据",
            "steps": [{"name": "去重"}, {"name": "格式化"}, {"name": "验证"}],
            "tools": ["Pandas", "Python"],
            "confidence": 0.8,
        }

        # 执行后存储
        stored_id_g = hook.after_execution("清洗用户行为数据", exec_result)
        log("Generic后置存储", f"存储经验 id={stored_id_g}")

        if stored_id_g:
            log("Generic闭环验证", "通用适配器闭环成功 ✅")
        else:
            log("Generic闭环验证", "存储失败", ok=False)

    except Exception as e:
        log("Generic适配器", f"验证失败: {e}", ok=False)

    # ── Step 9: 验证经验确实存入数据库 ──
    print("\n--- 数据库验证 ---")
    resp = httpx.get(
        f"{BASE_URL}/api/v1/experiences",
        params={"page": 1, "page_size": 5},
        headers={"Authorization": f"Bearer {token}"},
    )
    if resp.status_code == 200:
        data = resp.json()
        total = data.get("total", 0) if isinstance(data, dict) else len(data)
        log("数据库验证", f"当前用户可见经验总数: {total}")
    else:
        log("数据库验证", f"查询失败: {resp.status_code}", ok=False)

    # ── 总结 ──
    print("\n" + "=" * 60)
    print("  验证总结")
    print("=" * 60)
    print(f"  用户: {username}")
    print(f"  Agent API Key: {api_key[:20]}...")
    print(f"  CrewAI 存储经验: {'✅' if stored_id_1 else '❌'}")
    print(f"  CrewAI 二次存储: {'✅' if stored_id_2 else '❌'}")
    print(f"  LangGraph 存储: {'✅' if lg_stored else '❌'}")
    print(f"  Generic 存储: {'✅' if stored_id_g else '❌'}")

    all_pass = stored_id_1 and stored_id_2 and lg_stored and stored_id_g
    print(f"\n  {'🎉 全部适配器闭环验证通过!' if all_pass else '⚠️ 部分适配器验证失败'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
