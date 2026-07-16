# Aevum（薪火）OS - 变更日志

---

## [Unreleased]

### Added - 2026-07-16 (Phase 9 补充: Agent SDK + GEG 前端 + 日志)

#### Agent SDK (AevumClient)
- `backend/aevum/` Python SDK 包
  - `client.py` AevumClient: search/recommend/create_experience/get/list + MemoryContext 自动记忆上下文
  - `models.py` Experience + SearchResult 数据模型 (含 summary 助手方法)
  - `demo.py` 演示场景: 首次执行(45s) -> 二次执行(12s, 效率提升 73%)
  - 15 个单元测试
- 核心价值闭环验证通过: Agent 执行前检索经验 -> 跳过试错 -> 执行后自动沉淀

#### GEG 前端 (fork/improve/cite)
- 经验详情页 `frontend/app/(dashboard)/experiences/[id]/page.tsx`
  - Fork: 一键分叉, 创建副本 + fork 关系边, 自动跳转到新经验
  - Improve: 内联表单 (意图/有效做法/失败项/原因), 创建 improvement 关系边
  - Cite: 按领域搜索经验, 选择或输入 ID, 创建 citation 关系边
- 经验列表页 `frontend/app/(dashboard)/experiences/page.tsx`
  - 每条经验卡片新增 Fork 快捷按钮 (紫色 GitFork 图标)

#### Fork/Improve/Cite 全链路日志
- `backend/app/api/v1/governance.py` API 层日志: [API:FORK]/[API:IMPROVE]/[API:CITE]
- `backend/app/services/governance/versioning.py` 业务层日志: [FORK]/[IMPROVE]/[CITE]
- `backend/app/api/v1/experiences.py` 通用关系 API 日志: [API:ADD_RELATION]
- 每条日志含关键 ID (experience_id/relation_id/user_id), 便于追踪操作链路

### Fixed - 2026-07-16 (SDK 验证 + 前端修复)

- 修复 `frontend/lib/auth-store.ts` hydrate() 只恢复 token 不恢复 user 对象, 刷新后用户信息和退出按钮消失
- 修复 `frontend/lib/api-client.ts` fetchAPI 对 204 No Content 响应调用 res.json() 抛异常, 导致 DELETE 后列表不刷新
- 修复 `backend/app/api/v1/experiences.py` 经验创建时不生成 embedding, 导致向量搜索找不到新经验
- 修复 `backend/app/api/v1/experiences.py` 新经验 evaluation_status 默认 "pending" 被搜索过滤, 改为 API 创建时设 "evaluated"
- 修复 `backend/app/api/deps.py` get_optional_user 只检查 JWT 不检查 API Key, Agent 无法搜索用户级经验
- 修复 `backend/app/services/retrieval/priority_chain.py` _search_global 向量搜索返回空时不回退关键词搜索 (HashEmbedder 场景)

### Added - 2026-07-16 (Phase 8-9: 产品化升级 + GEG 全球经验网络 + Human World)

#### Phase 8: 产品化升级

- 用户认证系统（JWT + API Key 双认证）
  - `app/models/user.py` User 模型（id/email/role/is_active）
  - `app/models/agent.py` Agent 模型（name/api_key/permissions）
  - `app/api/v1/auth.py` 注册/登录/获取当前用户
  - `app/api/deps.py` get_current_user / get_optional_user / get_current_agent
  - `app/core/security.py` JWT 生成/验证 + API Key 校验 + bcrypt 密码哈希
  - 迁移 0002: users + agents 表
- 管理员 API（RBAC 角色控制）
  - `app/api/v1/admin.py` 用户管理/经验审核/系统统计/Agent 管理
- 经验治理层
  - `app/services/governance/trust.py` TrustScorer（多维信任评分）
  - `app/services/governance/decay.py` DecayManager（时间衰减因子）
  - `app/services/governance/lineage.py` LineageTracker（经验谱系追踪）
  - `app/api/v1/governance.py` 信任评分/谱系 API
  - 迁移 0003: trust_score + evaluation_status 字段
- 前端登录/注册页面
  - `frontend/app/login/page.tsx` 登录表单
  - `frontend/app/register/page.tsx` 注册表单（含密码校验）
  - `frontend/lib/auth-store.ts` Zustand 认证状态管理
  - `frontend/app/(dashboard)/layout.tsx` 路由守卫 + 用户信息 + 退出
- 前端管理员/Agent/治理页面
  - `frontend/app/(dashboard)/admin/page.tsx` 管理后台（用户/经验/统计）
  - `frontend/app/(dashboard)/agents/page.tsx` Agent 管理
  - `frontend/app/(dashboard)/governance/page.tsx` 经验治理

#### Phase 9: GEG 全球经验网络 + Human World

- Experience visibility 字段（三级可见性）
  - private（仅创建者）/ community（同社区）/ public（所有人）
  - 迁移 0004: visibility 字段
  - 全链路过滤：repository / matcher / priority_chain / API
- 优先级链四级检索
  - Level 1: 用户级（搜索自己的所有经验）
  - Level 2: 社区级（community + public，排除自己的）
  - Level 3: 全球级（仅 public）
  - Level 4: 外部网络（可插拔 ExternalSearchProvider，优雅降级）
  - `app/services/retrieval/external.py` HTTPExternalSearchProvider
- 信任评分接入检索排序
  - `app/services/retrieval/ranker.py` trust_score 加权 + decay_factor 乘法惩罚
- Community 表 + API
  - `app/models/community.py` Community + user_community 多对多
  - `app/api/v1/communities.py` 创建/列表/详情/加入/离开/成员
  - 迁移 0005: communities + user_community 表
  - 优先级链 Level 2 社区隔离过滤（community_id 真实过滤）
- Human World（双世界架构）
  - `app/models/human_expression.py` HumanExpression（人机分离四原则）
  - `app/api/v1/human.py` 表达 CRUD + 语义搜索 observe
  - 迁移 0006: human_expressions 表
- WorldBridge 桥接
  - `app/models/world_bridge.py` WorldBridge（4种桥接类型）
  - `app/api/v1/human.py` POST/GET /bridge 端点
  - 迁移 0007: world_bridges 表
  - inspiration / observation / recommendation / reflection
- 前端人类表达页面
  - `frontend/app/(dashboard)/human/page.tsx` 时间线 + 语义搜索

### Fixed - 2026-07-16 (Phase 8-9 初始修复)

- 修复 9 个预存前端测试失败（API URL 路径 /api -> /api/v1 不匹配）
- 修复数据库迁移未应用导致前端无法显示经验（迁移 0004-0007 未执行）
- 修复前端 .next 缓存导致旧代码运行（清除缓存并重启）

### Added - 2026-07-14 (Phase 0-7: MVP)

- 项目 Git 仓库初始化
- `.gitignore` 文件（Python + Node.js + IDE + OS）
- `.env.example` 环境变量模板
- 后端骨架：
  - `backend/pyproject.toml` 项目配置（FastAPI, SQLAlchemy, Alembic, Celery, pgvector 等）
  - `backend/requirements.txt` 依赖列表
  - `backend/app/main.py` FastAPI 应用入口
  - `backend/app/core/config.py` Pydantic Settings 配置
  - `backend/app/core/database.py` 异步 SQLAlchemy 数据库连接
  - `backend/app/api/deps.py` 依赖注入
  - `backend/app/models/`, `schemas/`, `services/` 目录结构（含4个子服务模块）
  - `backend/tests/conftest.py` pytest 配置和 fixtures
  - `backend/Dockerfile` 后端容器镜像
- 前端骨架：
  - Next.js 16 + React 19 + TypeScript + Tailwind CSS v4 项目
  - Dashboard 布局（侧边栏导航）
  - Dashboard 总览页（指标卡片占位）
  - 经验管理页、任务执行页、指标监控页（占位）
  - API 客户端封装（`lib/api-client.ts`）
  - TypeScript 类型定义（`types/index.ts`：Experience, SystemMetrics, TaskExecution）
  - `frontend/Dockerfile` 多阶段构建
  - `frontend/.env.local` 环境变量
- Docker 环境：
  - `docker-compose.yml` 开发环境编排（PostgreSQL+pgvector, Redis, Backend, Worker, Frontend）
  - `docker-compose.prod.yml` 生产环境编排
  - `nginx.conf` 反向代理配置
- 项目状态文件（`.trae/documents/` 下 10 个文件）
- 上线执行计划（`.trae/documents/Aevum_薪火OS_上线计划.md`）

### Added - 2026-07-14 (Phase 1-7: 核心能力)

- Phase 1: 经验数据模型（Experience ORM + Schema + 8步流水线）
- Phase 2: 经验执行引擎（工具注册 + 收敛控制 + 执行追踪）
- Phase 3: 经验存储与检索（pgvector 向量匹配 + 排序）
- Phase 4: 评估层（任务评估 + 经验评估 + 系统指标）
- Phase 5: 前端 Dashboard（经验管理 + 任务执行 + 指标监控）
- Phase 6: 集成测试（E2E 8步流水线 + API 健康检查 + 压测）
- Phase 7: 冷启动（10,000 条种子经验入库）
