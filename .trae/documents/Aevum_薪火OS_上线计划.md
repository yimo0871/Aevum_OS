# Aevum（薪火）OS — 上线执行计划

> 本计划遵循 `Autonomous_Project_Execution_Charter.md` 的全部执行原则。
> 最高原则：**项目最终成功 > 系统整体质量 > 长期可维护性 > 用户目标 > 当前任务 > 默认流程**

---

## 一、摘要

Aevum（薪火）OS 当前处于**纯概念设计阶段**，拥有完整的架构蓝图（v2文档，490行）但零代码实现。本计划定义了从零到上线的完整路径：技术选型、项目初始化、分阶段开发、质量保证、冷启动策略和部署方案。

**目标**：交付一个可运行、可测试、可维护的 SaaS Web 平台，实现薪火 OS 的核心经验闭环——从 Agent 执行到经验沉淀、检索、评估的完整 8 步流水线。

---

## 二、当前状态分析

### 2.1 已有资产

| 资产 | 文件 | 状态 |
|------|------|------|
| 产品路演文档 | `Aevum_薪火OS_产品路演.md` | 完成（57行，愿景陈述） |
| 架构总结 v1 | `Aevum_薪火OS_会话总结.md` | 完成（127行，基础架构） |
| 架构总结 v2 | `Aevum_薪火OS_会话总结_v2.md` | 完成（490行，完整蓝图） |
| 项目执行宪章 | `Autonomous_Project_Execution_Charter.md` | 完成（267行，执行规范） |

### 2.2 缺失项

| 缺失项 | 影响 |
|--------|------|
| 任何代码实现 | 无法运行、无法验证 |
| Git 仓库 | 无版本控制 |
| 项目结构 | 无组织骨架 |
| 依赖配置 | 无构建环境 |
| 测试框架 | 无质量保证 |
| 项目状态文件 | 无法持续维护进度（宪章第三章要求） |

### 2.3 架构蓝图核心要素（来自 v2 文档）

- **六层架构**：Human Expression → Agent Execution → Experience → Retrieval & Inference → Evaluation → Governance & Evolution
- **Experience 数据结构**：id, timestamp, context, intent, execution, outcome, reflection, reusable_patterns, confidence_score, provenance, version
- **8 步经验流水线**：检索 → 选择 → 执行 → 记录 → 生成 → 评估 → 存储 → 更新索引
- **人机分离四原则** + **跨世界桥接**（四种链接类型）
- **检索优先级链**：自身经验 → 社区经验 → 全球经验 → 外部网络
- **收敛控制**：最大迭代限制、改进阈值、停滞检测、终止保证
- **GEG 全球经验网络**：节点(Experience) + 边(reuse/citation/fork/improvement/dependency) + 信任模型

---

## 三、技术选型决策

### 3.1 技术栈（推荐方案）

| 层面 | 技术 | 理由 |
|------|------|------|
| **后端语言** | Python 3.12+ | AI/LLM 生态最成熟，与 Agent 框架天然兼容 |
| **后端框架** | FastAPI | 高性能异步、自动 OpenAPI 文档、类型安全、生态丰富 |
| **前端框架** | Next.js 15 + React 19 | SSR/SSG、App Router、文件系统路由、Server Components |
| **前端语言** | TypeScript (strict mode) | 类型安全，减少运行时错误 |
| **UI 组件库** | Tailwind CSS + shadcn/ui | 高质量设计、可定制、轻量 |
| **关系数据库** | PostgreSQL 16 | 成熟稳定、JSON/JSONB 支持、pgvector 扩展支持向量检索 |
| **向量检索** | pgvector (PostgreSQL 扩展) | MVP 阶段不引入额外数据库，降低运维复杂度 |
| **图存储** | PostgreSQL + JSONB（MVP）→ Neo4j（后期） | MVP 用关系型模拟图关系，避免过度工程化 |
| **缓存/队列** | Redis 7 | 缓存、会话、异步任务队列 |
| **异步任务** | Celery + Redis broker | 经验生成流水线异步化 |
| **容器化** | Docker + Docker Compose | 一致的开发/部署环境 |
| **代码规范** | Ruff + Black（Python）/ ESLint + Prettier（TS） | 统一编码风格 |
| **测试** | pytest（后端）/ Vitest + Playwright（前端） | 单元 + 集成 + E2E |
| **CI/CD** | GitHub Actions | 自动测试、构建、部署 |

### 3.2 MVP 范围决策

六层架构中，MVP 实现 **4 层核心闭环**，暂缓 2 层：

| 层级 | MVP 决策 | 理由 |
|------|----------|------|
| 1. Human Expression | **简化**：仅实现基础用户输入接口，不做完整非结构化存储 | 人机分离原则保留，但完整表达层非核心闭环必需 |
| 2. Agent Execution | **完整实现** | 核心入口，执行任务、生成 trace |
| 3. Experience | **完整实现** | 核心数据层，Experience 对象 CRUD + 图谱存储 |
| 4. Retrieval & Inference | **完整实现** | 经验检索匹配，四级优先级链 |
| 5. Evaluation | **完整实现** | 任务评估 + 经验评估 + 系统指标 |
| 6. Governance & Evolution | **简化**：仅实现版本控制和基本信任评分 | fork/merge/decay 后期迭代 |

**核心闭环**：执行 → 记录 → 生成经验 → 评估 → 存储 → 检索复用（8 步流水线的完整实现）

---

## 四、项目结构规划

```
aevum/
├── backend/                          # Python FastAPI 后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                   # FastAPI 入口
│   │   ├── core/                     # 核心配置
│   │   │   ├── config.py             # 环境配置
│   │   │   ├── database.py           # 数据库连接
│   │   │   └── security.py           # 认证授权
│   │   ├── api/                      # API 路由层
│   │   │   ├── v1/
│   │   │   │   ├── experiences.py    # 经验 CRUD
│   │   │   │   ├── execution.py      # 任务执行
│   │   │   │   ├── retrieval.py      # 经验检索
│   │   │   │   ├── evaluation.py     # 评估接口
│   │   │   │   └── dashboard.py      # Dashboard 数据
│   │   │   └── deps.py               # 依赖注入
│   │   ├── models/                   # 数据模型（SQLAlchemy ORM）
│   │   │   ├── experience.py         # Experience 对象
│   │   │   ├── execution.py          # 执行记录
│   │   │   ├── evaluation.py         # 评估记录
│   │   │   └── user.py               # 用户模型
│   │   ├── schemas/                  # Pydantic 模型（API 契约）
│   │   │   ├── experience.py
│   │   │   ├── execution.py
│   │   │   └── evaluation.py
│   │   ├── services/                 # 业务逻辑层
│   │   │   ├── execution/            # Agent 执行层
│   │   │   │   ├── engine.py         # 执行引擎
│   │   │   │   ├── trace.py          # 追踪记录
│   │   │   │   └── pipeline.py       # 8步流水线编排
│   │   │   ├── experience/           # 经验层
│   │   │   │   ├── repository.py     # 经验存储
│   │   │   │   ├── graph.py          # 图谱关系管理
│   │   │   │   └── factory.py        # 经验对象生成
│   │   │   ├── retrieval/            # 检索层
│   │   │   │   ├── matcher.py        # 相似度匹配
│   │   │   │   ├── ranker.py         # 排序评分
│   │   │   │   └── priority_chain.py # 四级优先级链
│   │   │   └── evaluation/           # 评估层
│   │   │       ├── task_evaluator.py # 任务评估
│   │   │       ├── experience_evaluator.py  # 经验评估
│   │   │       └── metrics.py        # 系统指标
│   │   └── utils/                    # 工具函数
│   ├── tests/                        # 测试
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   ├── alembic/                      # 数据库迁移
│   ├── requirements.txt
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                         # Next.js 前端
│   ├── src/
│   │   ├── app/                      # App Router
│   │   │   ├── (dashboard)/          # Dashboard 页面组
│   │   │   │   ├── page.tsx          # 总览
│   │   │   │   ├── experiences/      # 经验管理
│   │   │   │   ├── execution/        # 任务执行
│   │   │   │   └── metrics/          # 指标监控
│   │   │   ├── layout.tsx
│   │   │   └── api/                  # API Routes（BFF）
│   │   ├── components/               # UI 组件
│   │   │   ├── ui/                   # 基础组件（shadcn/ui）
│   │   │   ├── experience/           # 经验相关组件
│   │   │   ├── graph/                # 图谱可视化
│   │   │   └── metrics/              # 指标图表
│   │   ├── lib/                      # 工具库
│   │   ├── hooks/                    # React Hooks
│   │   └── types/                    # TypeScript 类型
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── Dockerfile
├── docker-compose.yml                # 开发环境编排
├── docker-compose.prod.yml           # 生产环境编排
├── .github/
│   └── workflows/
│       ├── backend-ci.yml            # 后端 CI
│       ├── frontend-ci.yml           # 前端 CI
│       └── deploy.yml                # 部署
├── docs/                             # 项目文档
│   ├── architecture/                 # 架构文档
│   └── api/                          # API 文档
├── scripts/                          # 脚本
│   ├── bootstrap_seeds.py            # 冷启动种子数据
│   └── setup_dev.sh                  # 开发环境初始化
├── .trae/
│   └── documents/                    # 项目状态文件（宪章第三章要求）
│       ├── PROJECT_STATE.md          # 项目状态总览
│       ├── ROADMAP.md                # 总体路线图
│       ├── MILESTONES.md             # 里程碑
│       ├── TASKS.md                  # 任务跟踪
│       ├── DECISIONS.md              # 决策记录（ADR）
│       ├── CHANGELOG.md              # 变更日志
│       ├── RISKS.md                  # 风险登记
│       ├── TEST_REPORT.md            # 测试报告
│       ├── ARCHITECTURE.md           # 架构文档
│       └── KNOWLEDGE.md              # 知识沉淀
├── .gitignore
├── .env.example
├── Makefile                          # 常用命令快捷方式
└── README.md
```

---

## 五、分阶段开发计划

### Phase 0：项目初始化（基础设施）

**目标**：建立可运行的开发环境和项目骨架。

**任务清单**：

1. **Git 仓库初始化**
   - `git init`
   - 创建 `.gitignore`（Python、Node.js、IDE、环境变量）
   - 初始提交

2. **后端骨架搭建**
   - 创建 `backend/` 目录结构
   - `pyproject.toml`：依赖管理（FastAPI, SQLAlchemy, Alembic, Pydantic, Celery, Redis, psycopg2, pgvector, httpx, ruff, black, pytest）
   - `app/main.py`：FastAPI 应用入口
   - `app/core/config.py`：环境配置（Pydantic Settings）
   - `app/core/database.py`：PostgreSQL 连接（异步 SQLAlchemy）
   - `requirements.txt`：锁定依赖

3. **前端骨架搭建**
   - `npx create-next-app@latest frontend --typescript --tailwind --app`
   - 集成 shadcn/ui
   - 配置 ESLint + Prettier
   - 基础 Layout 组件

4. **Docker 开发环境**
   - `docker-compose.yml`：PostgreSQL(+pgvector) + Redis + Backend + Frontend
   - `backend/Dockerfile`：Python 运行时
   - `frontend/Dockerfile`：Node 运行时

5. **项目状态文件初始化**（宪章第三章）
   - 在 `.trae/documents/` 下创建全部状态文件
   - `PROJECT_STATE.md`：当前阶段、进度总览
   - `ROADMAP.md`：总体路线图（Phase 0-7）
   - `MILESTONES.md`：里程碑定义与验收标准
   - `TASKS.md`：任务看板
   - `DECISIONS.md`：架构决策记录
   - `RISKS.md`：风险登记
   - `ARCHITECTURE.md`：技术架构文档
   - `KNOWLEDGE.md`：知识沉淀

6. **开发工具配置**
   - `Makefile`：常用命令（make dev, make test, make lint, make migrate）
   - `.env.example`：环境变量模板

**验收标准**：
- `docker-compose up` 可以启动全部服务
- 后端 `http://localhost:8000/docs` 可访问 API 文档
- 前端 `http://localhost:3000` 可访问首页
- 项目状态文件已创建且有初始内容

---

### Phase 1：核心数据层（Experience Layer）

**目标**：实现 Experience 对象的完整数据模型和存储。

**任务清单**：

1. **数据库 Schema 设计与迁移**
   - `alembic init alembic`
   - Experience 表：id(UUID), timestamp, context(JSONB), intent(TEXT), execution(JSONB), outcome(JSONB), reflection(JSONB), reusable_patterns(JSONB), confidence_score(FLOAT), provenance(JSONB), version(INT), created_at, updated_at
   - ExperienceRelation 表：id, source_id, target_id, relation_type(ENUM: reuse/citation/fork/improvement/dependency), weight, created_at
   - ExecutionTrace 表：id, experience_id, steps(JSONB), tools(JSONB), trace(JSONB), duration, status
   - pgvector 扩展：为 Experience 添加 embedding 列（VECTOR(1536)）

2. **ORM 模型**（`backend/app/models/`）
   - `experience.py`：Experience ORM 模型
   - `execution.py`：ExecutionTrace ORM 模型
   - 关系映射

3. **Pydantic Schema**（`backend/app/schemas/`）
   - `ExperienceCreate`：创建请求
   - `ExperienceResponse`：响应
   - `ExperienceUpdate`：更新请求
   - `ExperienceWithRelations`：含关系的完整对象

4. **经验存储服务**（`backend/app/services/experience/`）
   - `repository.py`：CRUD 操作
   - `graph.py`：图谱关系管理（添加/查询关系）
   - `factory.py`：从执行记录生成 Experience 对象

5. **API 路由**（`backend/app/api/v1/experiences.py`）
   - `POST /api/v1/experiences` — 创建经验
   - `GET /api/v1/experiences/{id}` — 获取单条
   - `GET /api/v1/experiences` — 列表（分页、过滤）
   - `PUT /api/v1/experiences/{id}` — 更新
   - `DELETE /api/v1/experiences/{id}` — 删除
   - `POST /api/v1/experiences/{id}/relations` — 添加关系
   - `GET /api/v1/experiences/{id}/relations` — 查询关系

6. **单元测试**
   - 模型测试
   - Schema 验证测试
   - Repository CRUD 测试
   - API 端点测试

**验收标准**：
- Experience 对象可以完整 CRUD
- JSONB 字段正确存储和查询
- pgvector embedding 列可用
- 图谱关系可添加和查询
- 单元测试覆盖率 ≥ 80%

---

### Phase 2：Agent 执行层（Agent Execution Layer）

**目标**：实现任务执行框架和 8 步经验流水线。

**任务清单**：

1. **执行引擎**（`backend/app/services/execution/`）
   - `engine.py`：任务执行核心引擎
     - `execute_task(task_input)` — 执行入口
     - `call_tool(tool_name, params)` — 工具调用接口
     - `run_workflow(workflow_def)` — 工作流执行
   - `trace.py`：执行追踪记录器
     - 记录每步操作、工具调用、中间结果
     - 生成结构化 trace 对象
   - `pipeline.py`：8 步流水线编排器
     - Step 1: retrieve_similar_experiences（调用检索层）
     - Step 2: select_best_workflows
     - Step 3: execute_task
     - Step 4: record_full_trace
     - Step 5: generate_experience_object（调用经验工厂）
     - Step 6: evaluate_experience（调用评估层）
     - Step 7: store_into_graph（调用经验存储）
     - Step 8: update_reuse_index
     - **失败条件**：未生成 Experience → 任务标记无效

2. **工具调用抽象**
   - 定义 `Tool` 基类：`name`, `description`, `execute(params) -> result`
   - 内置工具：HTTP 请求、Shell 命令、文件操作
   - 工具注册机制

3. **收敛控制实现**（`backend/app/services/execution/`）
   - `convergence.py`：收敛控制器
     - 最大迭代限制（Experience: 3次, Workflow: 2次, Evaluation: 2次, Retrieval: 2次）
     - 改进阈值检查（Δ performance ≥ ε）
     - 停滞检测（连续2次无改进 → 冻结 → 回滚）
     - 终止保证

4. **API 路由**（`backend/app/api/v1/execution.py`）
   - `POST /api/v1/execution/tasks` — 提交任务
   - `GET /api/v1/execution/tasks/{id}` — 查询任务状态
   - `GET /api/v1/execution/tasks/{id}/trace` — 获取执行追踪
   - `GET /api/v1/execution/tasks/{id}/experience` — 获取生成的经验

5. **异步任务处理**
   - Celery 任务定义：`execute_task_async`
   - Redis 作为 broker
   - 任务状态追踪

6. **测试**
   - 执行引擎单元测试
   - 流水线集成测试（模拟完整 8 步）
   - 收敛控制边界测试
   - 工具调用测试

**验收标准**：
- 任务可以提交并异步执行
- 8 步流水线完整运行，每步有记录
- 执行追踪完整记录
- 未生成 Experience 的任务被正确标记为无效
- 收敛控制在迭代超限时正确终止
- 测试覆盖率 ≥ 80%

---

### Phase 3：检索层（Retrieval & Inference Layer）

**目标**：实现经验检索匹配和四级优先级链。

**任务清单**：

1. **相似度匹配**（`backend/app/services/retrieval/`）
   - `matcher.py`：
     - 上下文相似度计算（基于 embedding 向量余弦相似度）
     - 语义匹配（LLM 辅助，可选）
   - `embedder.py`：文本向量化（使用 OpenAI embedding API 或本地模型）

2. **排序评分**（`backend/app/services/retrieval/ranker.py`）
   - 匹配评分函数实现：
     ```
     score = f(
       context_similarity,    # 上下文相似度
       success_rate,          # 历史成功率
       reuse_count,           # 复用次数
       domain_distance,       # 领域距离
       recency,               # 时效性
       confidence             # 置信度
     )
     ```
   - 权重可配置
   - 支持多种排序策略

3. **四级优先级链**（`backend/app/services/retrieval/priority_chain.py`）
   - Priority 1: 用户自身经验图谱
   - Priority 2: 社区经验图谱
   - Priority 3: 全球经验图谱
   - Priority 4: 外部网络数据（兜底）
   - 逐级检索，上级有结果则不查下级

4. **检索索引**
   - pgvector HNSW 索引
   - 领域/任务类型 B-tree 索引
   - 复用索引（Step 8 更新）

5. **API 路由**（`backend/app/api/v1/retrieval.py`）
   - `POST /api/v1/retrieval/search` — 搜索经验
   - `GET /api/v1/retrieval/recommend` — 推荐经验（基于上下文）
   - `POST /api/v1/retrieval/match` — 计算匹配度

6. **测试**
   - 匹配精度测试
   - 排序正确性测试
   - 优先级链逐级降级测试
   - 性能测试（检索延迟）

**验收标准**：
- 输入任务上下文，返回相关经验列表
- 四级优先级链正确降级
- 匹配评分函数各因子可配置
- 检索延迟 < 500ms（10万条经验规模）
- 测试覆盖率 ≥ 80%

---

### Phase 4：评估层（Evaluation Layer）

**目标**：实现四类评估维度和系统级指标追踪。

**任务清单**：

1. **任务评估**（`backend/app/services/evaluation/task_evaluator.py`）
   - 评估单次任务执行质量
   - 维度：完成度、正确性、效率、资源消耗
   - 输出结构化评估结果

2. **经验评估**（`backend/app/services/evaluation/experience_evaluator.py`）
   - 评估经验对象本身的价值
   - 维度：可复用性、可靠性、覆盖度、时效性
   - 更新 confidence_score

3. **工作流评估**
   - 评估工作流整体效能
   - 维度：成功率、平均执行时间、复用率

4. **系统指标**（`backend/app/services/evaluation/metrics.py`）
   - 七个系统级追踪指标：
     - `experience_reuse_rate` — 经验复用率
     - `workflow_success_rate` — 工作流成功率
     - `cross_agent_transfer_rate` — 跨 Agent 经验迁移率
     - `external_dependency_ratio` — 外部依赖比例
     - `learning_velocity` — 学习速度
     - `convergence_speed` — 收敛速度
     - `human_intervention_rate` — 人类干预率
   - 指标计算与缓存

5. **评估数据模型**
   - Evaluation 表：id, target_type, target_id, evaluator, scores(JSONB), summary, created_at
   - SystemMetric 表：id, metric_name, value, timestamp, metadata(JSONB)

6. **API 路由**（`backend/app/api/v1/evaluation.py`）
   - `POST /api/v1/evaluation/tasks/{id}` — 评估任务
   - `POST /api/v1/evaluation/experiences/{id}` — 评估经验
   - `GET /api/v1/evaluation/metrics` — 获取系统指标
   - `GET /api/v1/evaluation/dashboard` — Dashboard 聚合数据

7. **测试**
   - 各评估器单元测试
   - 指标计算准确性测试
   - "无评估=无效输出" 原则验证

**验收标准**：
- 任务执行后自动生成评估结果
- 经验 confidence_score 基于评估动态更新
- 七个系统指标实时可查
- 未评估的经验被标记为"待评估"，不进入检索池
- 测试覆盖率 ≥ 80%

---

### Phase 5：前端 Dashboard

**目标**：实现 Web 界面，支持经验管理和可视化。

**任务清单**：

1. **基础布局**
   - 侧边栏导航（Dashboard / 经验管理 / 任务执行 / 指标监控 / 设置）
   - 顶栏（用户信息、通知）
   - 响应式设计

2. **Dashboard 总览页**
   - 系统指标卡片（7个核心指标）
   - 经验增长趋势图
   - 最近活动时间线
   - 经验复用率仪表盘

3. **经验管理页**
   - 经验列表（表格/卡片视图切换）
   - 筛选与搜索（领域、任务类型、成功率、置信度）
   - 经验详情页（完整 Experience 对象展示）
   - 经验图谱可视化（节点-边关系图，使用 react-flow 或 d3.js）
   - 创建/编辑经验表单

4. **任务执行页**
   - 任务提交表单（输入意图、上下文、约束）
   - 执行进度追踪（8 步流水线实时状态）
   - 执行结果展示（trace、生成的经验、评估结果）

5. **指标监控页**
   - 七个系统指标的时序图表
   - 评估报告查看
   - 趋势分析

6. **前端工程化**
   - API 客户端封装（typed fetch）
   - 状态管理（Zustand 或 React Query）
   - 错误处理与加载状态
   - 组件测试（Vitest + Testing Library）

**验收标准**：
- 所有核心页面可访问且数据正确
- 经验图谱可视化展示节点和关系
- 任务执行进度实时更新
- 指标图表准确渲染
- 响应式设计（桌面/平板）
- 前端测试覆盖率 ≥ 70%

---

### Phase 6：集成测试与部署

**目标**：全链路集成验证，Docker 化部署。

**任务清单**：

1. **端到端集成测试**
   - 完整流程测试：提交任务 → 执行 → 生成经验 → 评估 → 存储 → 检索复用
   - 人机分离原则验证
   - 收敛控制端到端验证
   - 多用户场景测试

2. **CI/CD 流水线**
   - `backend-ci.yml`：lint → test → build
   - `frontend-ci.yml`：lint → test → build
   - `deploy.yml`：构建镜像 → 推送 → 部署
   - PR 合并前自动运行 CI

3. **Docker 生产配置**
   - `docker-compose.prod.yml`：生产编排
   - 后端：gunicorn + uvicorn workers
   - 前端：Next.js standalone build
   - Nginx 反向代理
   - 数据库持久化卷

4. **性能测试**
   - API 压测（locust 或 k6）
   - 数据库查询优化
   - 向量检索性能验证
   - 前端 Lighthouse 评分

5. **安全检查**
   - 输入验证与 SQL 注入防护
   - CORS 配置
   - 环境变量管理（无硬编码密钥）
   - API 限流

6. **部署文档**
   - `docs/deployment.md`：部署步骤
   - `docs/development.md`：开发指南
   - README.md 更新

**验收标准**：
- 端到端测试全部通过
- CI/CD 流水线正常工作
- Docker 生产环境可一键部署
- API 压测满足性能要求（100并发，P95 < 1s）
- 无安全漏洞（基础扫描通过）
- 部署文档完整可执行

---

### Phase 7：冷启动与 Bootstrap

**目标**：完成种子经验生成，达到第一阶段目标。

**任务清单**：

1. **种子数据生成脚本**（`scripts/bootstrap_seeds.py`）
   - 合成任务生成器（多领域、多任务类型）
   - 模拟执行并生成 Experience 对象
   - 生成 10,000 条种子经验
   - 初始化评估数据

2. **Bootstrap 数据源集成**
   - 精选开放数据集导入
   - 开源工作流模板导入
   - 专家模板导入

3. **评估系统初始化**
   - 对种子经验批量评估
   - 初始化系统指标基线
   - 建立复用索引

4. **冷启动验证**
   - 验证检索精度（种子经验可被正确检索）
   - 验证评估覆盖率（所有种子经验有评估）
   - 验证图谱连通性（经验间有关系）

**验收标准**：
- 10,000 条种子经验成功入库
- 所有种子经验有评估结果和 confidence_score
- 检索功能在种子数据上正常工作
- 系统指标有初始基线值
- 复用索引可用

---

## 六、质量保证策略

### 6.1 测试策略

| 测试层级 | 工具 | 覆盖率目标 | 范围 |
|----------|------|-----------|------|
| 单元测试 | pytest / Vitest | ≥ 80% | 模块级逻辑验证 |
| 集成测试 | pytest / Vitest | ≥ 70% | API 端到端、数据库交互 |
| E2E 测试 | Playwright | 核心流程 | 用户关键操作路径 |
| 性能测试 | locust / k6 | — | API 响应时间、并发能力 |
| 安全测试 | bandit / npm audit | — | 依赖漏洞、代码安全 |

### 6.2 代码质量

| 维度 | 工具 | 标准 |
|------|------|------|
| Python 代码风格 | Ruff + Black | 零违规 |
| TypeScript 代码风格 | ESLint + Prettier | 零违规 |
| 类型安全 | mypy / tsc strict | 零类型错误 |
| 重复代码 | Ruff / ESLint | < 3% |
| 复杂度 | Ruff / ESLint | 圈复杂度 < 15 |

### 6.3 架构一致性

- 严格遵循六层架构分层，层间通过定义的接口通信
- Experience 对象的 Schema 是全系统统一契约
- 人机分离四原则在代码层面有强制约束（类型系统 + 验证中间件）
- 8 步流水线不可跳步（流水线编排器强制执行）

### 6.4 持续集成

- 每个 PR 必须通过全部 CI 检查才能合并
- CI 检查项：lint → type-check → unit-test → integration-test → build
- 主分支保护：不允许直接 push，必须 PR
- 版本标签：语义化版本（v0.1.0 起）

---

## 七、风险评估与缓解

| 风险 | 级别 | 缓解方案 |
|------|------|----------|
| pgvector 检索性能在大规模数据下下降 | 中 | 预留迁移到专用向量数据库（Qdrant/Milvus）的接口抽象 |
| LLM API 成本和延迟 | 高 | 设计缓存层；embedding 使用本地模型备选；LLM 调用可选 |
| 8 步流水线复杂度高，调试困难 | 中 | 每步独立可测试；完善的 trace 记录；逐步集成 |
| 经验图谱在 MVP 阶段用关系型模拟，后期迁移成本 | 低 | 从开始就用 JSONB + 关系表模拟图，迁移路径清晰 |
| 冷启动种子经验质量不足 | 中 | 多来源交叉验证；人工抽检；评估系统自动过滤低质经验 |
| 前端图谱可视化性能 | 中 | 使用虚拟化渲染；节点数超过阈值时聚类展示 |

---

## 八、项目状态维护方案（宪章第三章）

在 `.trae/documents/` 目录下维护以下文件，作为项目唯一可信数据来源：

| 文件 | 用途 | 更新时机 |
|------|------|----------|
| `PROJECT_STATE.md` | 当前阶段、进度百分比、阻塞项 | 每次开发会话开始/结束时 |
| `ROADMAP.md` | 总体路线图（Phase 0-7） | 阶段调整时 |
| `MILESTONES.md` | 里程碑定义与验收标准 | 里程碑完成时 |
| `TASKS.md` | 任务看板（待办/进行中/完成） | 任务状态变更时 |
| `DECISIONS.md` | 架构决策记录（ADR 格式） | 重大决策时 |
| `CHANGELOG.md` | 变更日志 | 每次提交时 |
| `RISKS.md` | 风险登记与缓解状态 | 风险变化时 |
| `TEST_REPORT.md` | 测试覆盖率与结果 | 每次测试运行后 |
| `ARCHITECTURE.md` | 技术架构文档 | 架构变更时 |
| `KNOWLEDGE.md` | 知识沉淀、踩坑记录 | 持续 |

**恢复流程**：每次新开发会话 → 先读 `PROJECT_STATE.md` 恢复上下文 → 继续推进。

---

## 九、假设与决策

### 9.1 关键假设

1. 用户拥有 OpenAI API Key（或兼容的 LLM API），用于 embedding 和可选的 LLM 辅助评估
2. 开发环境为 Windows，使用 Docker Desktop 运行 PostgreSQL + Redis
3. 部署目标为云服务器（AWS/阿里云/自建），支持 Docker
4. 第一版为单租户 SaaS（多租户后期迭代）

### 9.2 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 向量检索方案 | pgvector | MVP 阶段不引入额外数据库，降低复杂度 |
| 图存储方案 | PostgreSQL JSONB + 关系表 | 避免 Neo4j 运维成本，MVP 阶段够用 |
| MVP 层级范围 | 4 层核心闭环（执行+经验+检索+评估） | 实现完整 8 步流水线，验证核心价值 |
| 前端框架 | Next.js + React + shadcn/ui | 全栈能力、类型安全、设计质量 |
| 异步任务 | Celery + Redis | 经验生成流水线异步化，避免阻塞 API |
| 前端状态管理 | React Query（服务端状态）+ Zustand（客户端状态） | 关注点分离，减少样板代码 |

---

## 十、验证步骤

### 10.1 Phase 验证（每阶段结束）

每个 Phase 完成后执行：
1. 运行全部测试：`make test`
2. 代码质量检查：`make lint`
3. 类型检查：`make type-check`
4. 更新 `PROJECT_STATE.md` 和 `TEST_REPORT.md`
5. 验证该 Phase 的验收标准全部满足

### 10.2 上线前最终验证

1. **功能完整性**：8 步经验流水线端到端跑通
2. **数据完整性**：Experience 对象 Schema 一致性验证
3. **架构一致性**：六层架构分层清晰，接口定义完整
4. **性能达标**：API P95 < 1s，检索 < 500ms
5. **安全合规**：无硬编码密钥，输入验证完整，CORS 正确
6. **文档完整**：API 文档、部署文档、开发文档齐全
7. **冷启动完成**：10,000 条种子经验入库且可检索
8. **项目状态同步**：所有 `.trae/documents/` 文件为最新

---

## 十一、执行顺序与依赖关系

```
Phase 0 (项目初始化)
  └── Phase 1 (经验数据层)
       ├── Phase 2 (执行层) — 依赖 Phase 1 的经验存储
       │    └── Phase 3 (检索层) — 依赖 Phase 2 的执行上下文
       │         └── Phase 4 (评估层) — 依赖 Phase 2+3 的产出
       │              └── Phase 5 (前端) — 依赖 Phase 1-4 的 API
       │                   └── Phase 6 (集成部署) — 依赖全部
       │                        └── Phase 7 (冷启动) — 依赖可运行系统
       └── (Phase 1 完成后可并行启动前端骨架)
```

**关键路径**：Phase 0 → 1 → 2 → 3 → 4 → 6 → 7
**可并行**：Phase 5（前端）可在 Phase 4 进行时并行开发骨架

---

## 十二、下一步行动

计划批准后，立即执行 **Phase 0：项目初始化**，包括：
1. Git 仓库初始化
2. 后端/前端骨架搭建
3. Docker 开发环境配置
4. 项目状态文件创建
5. 首次提交

随后按 Phase 顺序自主推进，遵循宪章第四章"自主推进"原则，仅在需要产品方向决策或不可逆选择时暂停确认。
