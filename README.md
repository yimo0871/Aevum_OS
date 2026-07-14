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
git clone <repository-url>
cd Aevum_薪火OS
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入真实的 API Key 等配置
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
uvicorn app.main:app --reload

# 启动前端
cd frontend
npm install
npm run dev
```

### 4. 访问服务

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| API 文档 (ReDoc) | http://localhost:8000/redoc |

---

## 项目结构

```
aevum/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口
│   │   ├── core/         # 配置、数据库
│   │   ├── api/v1/       # REST API 路由
│   │   ├── models/       # ORM 模型
│   │   ├── schemas/      # Pydantic 模型
│   │   └── services/     # 业务逻辑（4个子模块）
│   └── tests/
├── frontend/             # Next.js 前端
│   ├── app/
│   │   ├── (dashboard)/  # Dashboard 页面组
│   │   └── layout.tsx
│   ├── lib/              # 工具库
│   └── types/            # TypeScript 类型
├── docker-compose.yml    # 开发环境
├── Makefile              # 常用命令
└── .trae/documents/      # 项目状态文件
```

---

## 技术栈

| 层面 | 技术 |
|------|------|
| 后端 | Python 3.12 + FastAPI + SQLAlchemy + Celery |
| 数据库 | PostgreSQL 16 + pgvector + Redis |
| 前端 | Next.js 16 + React 19 + TypeScript + Tailwind CSS |
| 部署 | Docker + Docker Compose |

---

## 开发命令

```bash
make help         # 查看所有命令
make dev          # 启动开发环境
make test         # 运行测试
make lint         # 代码检查
make format       # 代码格式化
make type-check   # 类型检查
make migrate      # 数据库迁移
```

---

## 项目状态

项目状态文件位于 `.trae/documents/`，是项目唯一可信的数据来源。

| 文件 | 用途 |
|------|------|
| `PROJECT_STATE.md` | 当前阶段与进度 |
| `ROADMAP.md` | 总体路线图 |
| `MILESTONES.md` | 里程碑与验收标准 |
| `ARCHITECTURE.md` | 技术架构文档 |
| `DECISIONS.md` | 架构决策记录 |

---

## 架构

薪火 OS 采用六层架构：

1. **Human Expression Layer** - 人类表达层（MVP: 简化）
2. **Agent Execution Layer** - Agent 执行层（MVP: 完整）
3. **Experience Layer** - 经验层（核心，MVP: 完整）
4. **Retrieval & Inference Layer** - 检索与推理层（MVP: 完整）
5. **Evaluation Layer** - 评估层（MVP: 完整）
6. **Governance & Evolution Layer** - 治理与演进层（MVP: 简化）

核心闭环：执行 -> 记录 -> 生成经验 -> 评估 -> 存储 -> 检索复用（8 步流水线）

---

## License

MIT
