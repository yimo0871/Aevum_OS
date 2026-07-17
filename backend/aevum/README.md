# Aevum SDK

**Agent 经验记忆层** — 让任何 Agent 框架在执行前检索相似经验（跳过试错），在执行后自动沉淀经验（复利积累）。

Aevum SDK 是框架无关的轻量客户端：执行前检索历史经验，执行后自动存储新经验。提供 LangGraph、CrewAI 专属适配器，以及面向任意框架的通用 Hook。

## 安装

```bash
pip install aevum

# 按需安装框架适配器
pip install "aevum[langgraph]"
pip install "aevum[crewai]"

# 开发环境
pip install "aevum[dev]"
```

> SDK 仅硬依赖 `httpx`。`langgraph` / `crewai` 为可选依赖，缺失时对应适配器仍可导入，仅在实际包裹对应框架对象时才需要安装。

## 快速开始

```python
from aevum import AevumClient

client = AevumClient(api_key="ak_xxx", base_url="http://localhost:8000")

# 1. 执行前：检索相似经验
results = client.search("deploy React to Vercel", domain="frontend")
for r in results:
    print(r.summary())

# 2. 执行后：沉淀经验
client.create_experience(
    context={"domain": "frontend", "task_type": "deployment"},
    intent="deploy React to Vercel",
    outcome={"success": True, "metrics": {"deploy_time_s": 45}},
)

# 3. 高级：自动记忆上下文（进入检索，退出存储）
with client.memory("deploy React to Vercel", domain="frontend") as mem:
    result = your_agent.execute(...)
    mem.record_outcome(success=True, what_worked=["vercel deploy --prod"])
# 经验已自动存储
```

## 适配器

### LangGraph

```python
from aevum import AevumClient
from aevum.adapters.langgraph import AevumRunner

graph = build_my_graph().compile()
client = AevumClient(api_key="ak_xxx")

runner = AevumRunner(graph, client, domain="devops")

result = runner.invoke({"task": "deploy Flask app"})
# result["aevum_experiences"]     -> 检索到的历史经验摘要
# result["aevum_stored_experience_id"] -> 新存储的经验 id
```

异步执行：`await runner.ainvoke({"task": "..."})`。

节点级细粒度注入：

```python
from aevum.adapters.langgraph import with_experience_context

@with_experience_context(client, domain="devops")
def plan_node(state):
    # state["aevum_experiences"] 含历史经验摘要
    return {"plan": "..."}
```

### CrewAI

```python
from aevum import AevumClient
from aevum.adapters.crewai import AevumCrewWrapper

crew = Crew(agents=[...], tasks=[...])
client = AevumClient(api_key="ak_xxx")

wrapped = AevumCrewWrapper(crew, client, domain="devops")
result = wrapped.kickoff(inputs={"topic": "deploy Flask app"})

# 结果上附带 Aevum 元数据：
# result.aevum_experiences          -> 历史经验摘要列表
# result.aevum_experiences_found    -> 命中数量
# result.aevum_stored_experience_id -> 新存储的经验 id
# result.aevum_duration_s           -> 执行耗时
```

异步执行：`await wrapped.kickoff_async(inputs={...})`。

### Generic（任意框架）

适用于 AutoGen、LangChain Agent、自研框架等没有专属适配器的场景。

**手动 before/after：**

```python
from aevum import AevumClient
from aevum.adapters.generic import AevumHook

client = AevumClient(api_key="ak_xxx")
hook = AevumHook(client, domain="devops")

# 执行前：检索经验
experiences = hook.before_execution("deploy app")

# ... 你的框架执行 ...
result = my_framework.run("deploy app")

# 执行后：存储经验
hook.after_execution(
    "deploy app", result, success=True, what_worked=["docker"], tools=["docker", "kubectl"],
)
```

**上下文管理器（自动生命周期）：**

```python
from aevum.adapters.generic import AevumContext

with AevumContext(client, task="deploy app", domain="devops") as ctx:
    # ctx.experiences 含历史经验摘要
    result = my_framework.run("deploy app")
    ctx.record(success=True, what_worked=["docker"])
# 退出 with 块时经验已自动存储
```

## API 参考

### `AevumClient`

| 方法 | 说明 |
| --- | --- |
| `search(query, domain=None, task_type=None, limit=5)` | 检索相似经验，返回 `list[SearchResult]` |
| `recommend(query, domain=None, limit=3)` | 综合检索 + 排序推荐 |
| `create_experience(context, intent, outcome=None, execution=None, reflection=None, ...)` | 存储一条经验，返回创建的对象（含 id） |
| `get_experience(experience_id)` | 获取单条经验详情 |
| `list_experiences(page=1, page_size=20, domain=None)` | 列出经验 |
| `memory(task, domain="general", ...)` | 返回自动记忆上下文管理器 `MemoryContext` |

### 数据模型

- **`SearchResult`**：检索结果。字段 `id, intent, similarity, confidence_score, domain, task_type, success, what_worked, what_failed, why, tools`。方法 `summary()` 生成供 Agent 参考的摘要；`from_api(data)` 从 API 响应构建。
- **`Experience`**：经验对象。方法 `to_api()` 转为 API 请求体。

### 适配器

| 适配器 | 类 | 入口方法 |
| --- | --- | --- |
| LangGraph | `AevumRunner` | `invoke(input)` / `ainvoke(input)` |
| LangGraph 节点 | `with_experience_context` | 装饰器 |
| CrewAI | `AevumCrewWrapper` | `kickoff(inputs)` / `kickoff_async(inputs)` |
| Generic | `AevumHook` | `before_execution(task)` / `after_execution(task, result, ...)` |
| Generic | `AevumContext` | `with AevumContext(...) as ctx: ctx.record(...)` |

## 行为约定

所有适配器均遵循 **优雅降级** 原则：

- **检索失败**：返回空列表，不阻塞任务执行。
- **存储失败**：不影响主流程，结果中 `aevum_stored_experience_id` 为 `None`。

## License

MIT
