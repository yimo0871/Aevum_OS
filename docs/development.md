# Aevum（薪火）OS - 开发指南

## 项目结构

```
aevum/
├── backend/              # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py       # 应用入口
│   │   ├── core/         # 配置、数据库
│   │   ├── api/v1/       # REST API 路由
│   │   │   ├── experiences.py   # 经验 CRUD + 图谱关系
│   │   │   ├── execution.py     # 任务执行 + 8步流水线
│   │   │   ├── retrieval.py     # 经验检索
│   │   │   └── evaluation.py    # 评估 + 指标 + Dashboard
│   │   ├── models/       # SQLAlchemy ORM 模型
│   │   ├── schemas/      # Pydantic 模型（API 契约）
│   │   └── services/     # 业务逻辑层
│   │       ├── execution/    # 执行引擎 + 流水线 + 工具 + 收敛控制
│   │       ├── experience/   # 经验存储 + 图谱 + 工厂
│   │       ├── retrieval/    # 向量化 + 匹配 + 排序 + 优先级链
│   │       └── evaluation/   # 任务评估 + 经验评估 + 系统指标
│   ├── tests/            # 测试
│   │   ├── unit/         # 单元测试
│   │   ├── integration/  # 集成测试
│   │   └── e2e/          # 端到端测试
│   ├── alembic/          # 数据库迁移
│   └── pyproject.toml    # Python 项目配置
├── frontend/             # Next.js 前端
│   ├── app/
│   │   ├── (dashboard)/  # Dashboard 页面组
│   │   │   ├── page.tsx          # Dashboard 总览
│   │   │   ├── experiences/      # 经验管理
│   │   │   ├── execution/        # 任务执行
│   │   │   └── metrics/          # 指标监控
│   │   └── layout.tsx
│   ├── lib/              # API 客户端 + Provider
│   └── types/            # TypeScript 类型
├── docker-compose.yml    # 开发环境
├── docker-compose.prod.yml
├── Makefile
└── .trae/documents/      # 项目状态文件
```

## 开发流程

### 1. 启动开发环境

```bash
docker-compose up -d
```

### 2. 后端开发

```bash
# 进入后端容器
docker-compose exec backend bash

# 运行测试
pytest -v --cov=app

# 代码检查
ruff check . && black --check .

# 类型检查
mypy app/

# 数据库迁移
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### 3. 前端开发

```bash
# 进入前端容器
docker-compose exec frontend bash

# 开发服务器（热重载）
npm run dev

# 代码检查
npm run lint

# 构建
npm run build
```

## 架构原则

### 六层架构

1. **Human Expression Layer** - 人类表达（MVP: 简化）
2. **Agent Execution Layer** - Agent 执行（MVP: 完整）
3. **Experience Layer** - 经验（核心，MVP: 完整）
4. **Retrieval & Inference Layer** - 检索（MVP: 完整）
5. **Evaluation Layer** - 评估（MVP: 完整）
6. **Governance & Evolution Layer** - 治理（MVP: 简化）

### 人机分离四原则（不可违反）

1. 人类数据绝不直接进入经验图谱
2. Agent 不得改写人类表达
3. 人类输出仅供观察性使用
4. Agent 输出必须完全结构化且可评估

### 8 步经验流水线

```
Step 1: 检索相似经验 -> Step 2: 选择最佳工作流 -> Step 3: 执行任务
Step 4: 记录完整追踪 -> Step 5: 生成经验对象 -> Step 6: 评估经验
Step 7: 存入图谱 -> Step 8: 更新复用索引

失败条件：未生成 Experience -> 任务无效
```

### 核心原则

- **无评估 = 无效输出** - 未评估的经验不进入检索池
- **收敛控制** - 所有循环必须可终止
- **四级检索链** - 用户经验 > 社区经验 > 全球经验 > 外部网络

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 应用信息 |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger API 文档 |
| POST | `/api/v1/experiences` | 创建经验 |
| GET | `/api/v1/experiences` | 列出经验 |
| GET | `/api/v1/experiences/{id}` | 获取经验 |
| PUT | `/api/v1/experiences/{id}` | 更新经验 |
| DELETE | `/api/v1/experiences/{id}` | 删除经验 |
| POST | `/api/v1/experiences/{id}/relations` | 添加图谱关系 |
| GET | `/api/v1/experiences/{id}/relations` | 查询图谱关系 |
| POST | `/api/v1/execution/tasks` | 提交任务（同步8步流水线） |
| POST | `/api/v1/execution/tasks/async` | 提交任务（异步Celery） |
| GET | `/api/v1/execution/tasks/{id}/status` | 查询异步任务状态 |
| GET | `/api/v1/execution/tools` | 列出可用工具 |
| POST | `/api/v1/retrieval/search` | 搜索经验 |
| GET | `/api/v1/retrieval/recommend` | 推荐经验 |
| GET | `/api/v1/retrieval/priority-chain` | 优先级链详情 |
| POST | `/api/v1/evaluation/experiences/{id}` | 评估经验 |
| GET | `/api/v1/evaluation/metrics` | 获取系统指标 |
| GET | `/api/v1/evaluation/metrics/{name}/history` | 指标历史 |
| GET | `/api/v1/evaluation/dashboard` | Dashboard 聚合数据 |

## 项目状态

项目状态文件位于 `.trae/documents/`，是项目唯一可信的数据来源。每次开发会话开始时，先读取 `PROJECT_STATE.md` 恢复上下文。
