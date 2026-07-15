# Aevum（薪火）OS - Python SDK

供外部 Agent 接入 Aevum OS 的 Python 客户端库。

## 安装

SDK 依赖 `httpx`，请先安装：

```bash
pip install httpx
```

将 `sdk/` 目录加入项目路径，或直接复制 `aevum_client.py` 到你的项目中。

## 快速开始

```python
from sdk import AevumClient

# 初始化客户端（无需认证即可访问公开接口）
client = AevumClient(base_url="http://localhost:8000")

# 使用 JWT token 认证（可选）
client = AevumClient(base_url="http://localhost:8000", token="your-jwt-token")

# 使用 API Key 认证（可选）
client = AevumClient(base_url="http://localhost:8000", api_key="your-api-key")
```

## 主要功能

### 1. 提交任务执行

提交一个任务意图，系统将执行 8 步经验流水线并生成 Experience 对象。

```python
result = client.submit_task(
    intent="部署一个 Python FastAPI 服务到 Kubernetes",
    domain="devops",
    task_type="deployment",
    constraints={"cluster": "prod", "replicas": 3},
)
print(result["experience_id"])
```

### 2. 搜索经验

通过四级优先级链检索相似经验（用户经验 → 社区经验 → 全球经验 → 外部网络）。

```python
results = client.search_experiences(
    query="如何优化 PostgreSQL 查询性能",
    domain="data",
    limit=10,
)
for r in results:
    print(r["experience"]["intent"], r["score"])
```

### 3. 获取经验详情

```python
experience = client.get_experience("experience-uuid-here")
print(experience["intent"], experience["outcome"]["success"])
```

### 4. 列出经验

```python
page = client.list_experiences(page=1, page_size=20, domain="devops")
print(page["total"], len(page["items"]))
```

### 5. 获取 Dashboard 和系统指标

```python
dashboard = client.get_dashboard()
metrics = client.get_metrics()
```

## 认证方式

SDK 支持两种认证方式（优先使用 API Key）：

| 方式 | 参数 | Header |
|------|------|--------|
| API Key | `api_key="..."` | `X-API-Key: ...` |
| JWT Token | `token="..."` | `Authorization: Bearer ...` |

如果两者都未提供，则以匿名身份访问（仅限公开接口）。

## API 映射

| SDK 方法 | HTTP 接口 |
|----------|-----------|
| `submit_task()` | `POST /api/v1/execution/tasks` |
| `search_experiences()` | `POST /api/v1/retrieval/search` |
| `get_experience()` | `GET /api/v1/experiences/{id}` |
| `list_experiences()` | `GET /api/v1/experiences` |
| `get_dashboard()` | `GET /api/v1/evaluation/dashboard` |
| `get_metrics()` | `GET /api/v1/evaluation/metrics` |
