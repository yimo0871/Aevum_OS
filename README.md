# Aevum / 薪火 OS

> **Experience never fades. It compounds.**
> **经验不熄，代代相传。**

人类历史上第一个以"经验"为第一公民的操作系统 -- Agent 时代的 GitHub + Stack Overflow + Wikipedia 的融合体。

---

## 快速开始

### 前置要求

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Node.js](https://nodejs.org/) 20+ (前端开发)
- [Python](https://www.python.org/) 3.12+ (后端开发)
- [Make](https://www.gnu.org/software/make/) (可选，用于 Makefile 命令)

### 1. 克隆仓库

```bash
git clone https://github.com/yimo0871/Aevum_OS.git
cd Aevum_OS
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，按需填入 API Key 等配置
```

最小配置（仅本地开发，无语义搜索）：
- 无需修改任何值，默认配置即可启动

完整配置（启用火山引擎语义搜索）：
```env
OPENAI_API_KEY=你的火山引擎API Key
OPENAI_BASE_URL=https://ark.cn-beijing.volces.com/api/coding/v3
EMBEDDING_MODEL=doubao-embedding-vision
EMBEDDING_DIMENSION=1024
```

### 3. 启动开发环境

**方式一：Docker Compose（推荐）**

```bash
make up        # 后台启动全部服务
make logs      # 查看日志
```

**方式二：分别启动**

```bash
# 启动数据库和 Redis
docker-compose up -d db redis

# 启动后端
cd backend
pip install -r requirements.txt
alembic upgrade head    # 运行数据库迁移
uvicorn app.main:app --reload

# 启动前端
cd frontend
npm install
npm run dev
```

### 4. 验证服务

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端 | http://localhost:3000 | 登录/注册/Dashboard/经验管理 |
| 后端 API | http://localhost:8000 | REST API |
| Swagger 文档 | http://localhost:8000/docs | 交互式 API 文档 |
| ReDoc 文档 | http://localhost:8000/redoc | 只读 API 文档 |

**首次使用流程：**
1. 访问 http://localhost:3000/register 注册账号
2. 登录后进入 Dashboard
3. 在 Agent 管理页面注册一个 Agent，获取 API Key
4. 使用 API Key 通过 SDK 接入你的 Agent

---

## Agent SDK 快速上手

### 安装

```bash
pip install aevum

# 按需安装框架适配器
pip install "aevum[langgraph]"
pip install "aevum[crewai]"
```

### 基础用法

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

# 3. 高级：自动记忆上下文
with client.memory("deploy React to Vercel", domain="frontend") as mem:
    result = your_agent.execute(...)
    mem.record_outcome(success=True, what_worked=["vercel deploy --prod"])
```

### LangGraph 适配器

```python
from aevum import AevumClient
from aevum.adapters.langgraph import AevumRunner

graph = build_my_graph().compile()
client = AevumClient(api_key="ak_xxx")

runner = AevumRunner(graph, client, domain="devops")
result = runner.invoke({"task": "deploy Flask app"})
# result["aevum_experiences"]          -> 检索到的历史经验
# result["aevum_stored_experience_id"] -> 新存储的经验 id
```

### CrewAI 适配器

```python
from aevum import AevumClient
from aevum.adapters.crewai import AevumCrewWrapper

crew = Crew(agents=[...], tasks=[...])
client = AevumClient(api_key="ak_xxx")

wrapped = AevumCrewWrapper(crew, client, domain="devops")
result = wrapped.kickoff(inputs={"topic": "deploy Flask app"})
```

### 通用适配器（任意框架）

```python
from aevum.adapters.generic import AevumContext

with AevumContext(client, task="deploy app", domain="devops") as ctx:
    result = my_framework.run("deploy app")
    ctx.record(success=True, what_worked=["docker"])
```

> 所有适配器遵循**优雅降级**原则：检索失败返回空列表，存储失败不影响主流程。

完整 SDK 文档见 [backend/aevum/README.md](backend/aevum/README.md)。

---

## 生产部署

### 1. 准备生产配置

```bash
cp .env.production.example .env.production
# 编辑 .env.production，填入强密码和真实 API Key
```

**必须修改的配置项：**
```env
SECRET_KEY=使用 openssl rand -hex 32 生成
POSTGRES_PASSWORD=强密码
DATABASE_URL=postgresql+asyncpg://aevum:强密码@db:5432/aevum
OPENAI_API_KEY=你的火山引擎API Key
```

### 2. 启动生产环境

```bash
docker-compose -f docker-compose.prod.yml up -d
```

生产环境包含：
- Nginx 反向代理（80 端口）
- Gunicorn + Uvicorn workers（4 进程）
- PostgreSQL + pgvector
- Redis
- Celery Worker
- Next.js 前端

### 3. 验证部署

```bash
curl http://localhost/api/v1/health    # 健康检查
curl http://localhost/docs             # API 文档
```

### 4. 运行数据库迁移

```bash
docker exec aevum-backend-prod alembic upgrade head
```

### 5. 创建管理员账号

注册普通用户后，通过数据库手动提升为管理员：
```sql
UPDATE users SET is_admin = true WHERE email = 'your-email@example.com';
```

---

## 配置参考

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `APP_ENV` | `development` | 环境标识 |
| `APP_DEBUG` | `true` | 调试模式 |
| `DATABASE_URL` | 自动拼接 | PostgreSQL 连接串（为空时从 POSTGRES_* 拼接） |
| `POSTGRES_HOST` | `localhost` | 数据库主机 |
| `POSTGRES_PORT` | `5432` | 数据库端口 |
| `POSTGRES_DB` | `aevum` | 数据库名 |
| `POSTGRES_USER` | `aevum` | 数据库用户 |
| `POSTGRES_PASSWORD` | `aevum_dev_password` | 数据库密码 |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` | Celery Broker |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/1` | Celery Result Backend |
| `SECRET_KEY` | `dev-secret-key-change-in-production` | JWT 签名密钥（生产必须修改） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token 过期时间（分钟） |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | CORS 允许来源（JSON 数组） |
| `OPENAI_API_KEY` | (空) | LLM/Embedding API Key（留空使用本地 HashEmbedder） |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1` | LLM API 地址 |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding 模型名 |
| `EMBEDDING_DIMENSION` | `1024` | Embedding 维度 |
| `NODE_URL` | `http://localhost:8000` | 联邦节点 URL |
| `NODE_ID` | `local` | 联邦节点 ID |

### 检索权重调优

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `WEIGHT_CONTEXT_SIMILARITY` | 0.25 | 上下文相似度权重 |
| `WEIGHT_SUCCESS_RATE` | 0.15 | 成功率权重 |
| `WEIGHT_REUSE_COUNT` | 0.08 | 复用次数权重 |
| `WEIGHT_DOMAIN_DISTANCE` | 0.07 | 领域距离权重 |
| `WEIGHT_RECENCY` | 0.12 | 时间衰减权重 |
| `WEIGHT_CONFIDENCE` | 0.13 | 置信度权重 |
| `WEIGHT_TRUST_SCORE` | 0.20 | 信任评分权重 |

---

## 测试

### 运行全部测试

```bash
make test
```

### 后端测试

```bash
cd backend
pytest -v --cov=app --cov-report=term-missing

# 运行特定模块测试
pytest tests/unit/test_marketplace.py -v

# 运行并查看覆盖率
pytest --cov=app --cov-report=html
```

### 前端测试

```bash
cd frontend
npm test -- --run
```

### 测试基线

| 类型 | 数量 | 状态 |
|------|------|------|
| 后端单元测试 | 648 | ✅ 全通过 |
| 前端组件测试 | 64 | ✅ 全通过 |
| 端到端验证 | 4/4 | ✅ 全通过 |

---

## 开发命令

```bash
make help         # 查看所有命令
make dev          # 启动开发环境（Docker Compose）
make dev-backend  # 仅启动后端（热重载）
make up           # 后台启动全部服务
make down         # 停止全部服务
make logs         # 查看日志
make test         # 运行全部测试
make lint         # 代码检查（ruff + eslint）
make format       # 代码格式化（black + prettier）
make type-check   # 类型检查（mypy + tsc）
make migrate      # 数据库迁移
make db-reset     # 重置数据库（危险！）
make clean        # 清理构建产物
```

---

## 项目结构

```
Aevum_OS/
├── backend/                  # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py           # 应用入口
│   │   ├── core/             # 配置、数据库、安全
│   │   ├── api/v1/           # REST API 路由（12 个模块）
│   │   ├── models/           # ORM 模型（15 个表）
│   │   ├── schemas/          # Pydantic 请求/响应模型
│   │   └── services/         # 业务逻辑（8 个子模块）
│   │       ├── bootstrap/    # 引导流程
│   │       ├── evaluation/   # 评估
│   │       ├── execution/    # 执行
│   │       ├── experience/   # 经验管理
│   │       ├── federation/   # 联邦网络
│   │       ├── governance/   # 治理（审计/压缩/衰减/身份/信任/版本）
│   │       ├── llm/          # LLM Provider
│   │       ├── marketplace/  # 经验市场
│   │       └── retrieval/    # 检索（匹配/排序/嵌入）
│   ├── aevum/                # Agent SDK（pip installable）
│   │   ├── client.py         # AevumClient
│   │   └── adapters/         # 框架适配器（LangGraph/CrewAI/Generic）
│   ├── alembic/              # 数据库迁移（15 个版本）
│   └── tests/                # 单元测试（648 个）
├── frontend/                 # Next.js 前端
│   ├── app/
│   │   ├── (auth)/           # 登录/注册
│   │   └── (dashboard)/      # Dashboard/经验/检索/管理/Agent/治理/市场
│   ├── lib/                  # API 客户端
│   └── __tests__/            # 组件测试（64 个）
├── docker-compose.yml        # 开发环境
├── docker-compose.prod.yml   # 生产环境
├── .env.example              # 开发环境配置模板
├── .env.production.example   # 生产环境配置模板
├── Makefile                  # 常用命令
└── .trae/documents/          # 项目文档
```

---

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy 2.0 + Celery |
| 数据库 | PostgreSQL 16 + pgvector + Redis 7 |
| 前端 | Next.js 16 + React 19 + TypeScript + Tailwind CSS |
| Agent SDK | Python + httpx（支持 LangGraph / CrewAI / Generic） |
| LLM | 火山引擎 doubao-embedding-vision（OpenAI 兼容 API） |
| 部署 | Docker + Docker Compose + Nginx + Gunicorn |

---

## 架构

薪火 OS 采用六层架构：

1. **Human Expression Layer** - 人类表达层（双世界架构）
2. **Agent Execution Layer** - Agent 执行层
3. **Experience Layer** - 经验层（核心）
4. **Retrieval & Inference Layer** - 检索与推理层（向量搜索 + 优先级链）
5. **Evaluation Layer** - 评估层（自动 + 人机协同）
6. **Governance & Evolution Layer** - 治理与演进层（信任/版本/审计/压缩/市场/联邦）

核心闭环：执行 -> 记录 -> 生成经验 -> 评估 -> 存储 -> 检索复用

---

## 项目状态

项目状态文件位于 `.trae/documents/`，是项目唯一可信的数据来源。

| 文件 | 用途 |
|------|------|
| `PROJECT_STATE.md` | 当前阶段、进度、测试、迁移历史 |
| `ROADMAP.md` | 总体路线图与里程碑 |
| `CHANGELOG.md` | 变更日志 |
| `TECH_DEBT.md` | 技术债务清单 |
| `TEST_REPORT.md` | 测试报告 |

**当前状态：** 愿景 100% 达成（16/16），4/4 真实场景验证通过，648 后端测试 + 64 前端测试，15 个数据库迁移，技术债务高/中优先级全部修复。

---

## License

MIT
