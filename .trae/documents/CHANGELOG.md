# Aevum（薪火）OS - 变更日志

---

## [Unreleased]

### Docs - 2026-07-22 (README 完善 + 配置模板)

- `README.md` 完整重写：快速上手/Agent SDK/生产部署/配置参考/测试指南/项目结构
- `.env.example` 新建开发环境配置模板（覆盖所有必要配置项）
- `.env.production.example` 新建生产环境配置模板
- `.env.example` 补充 `ALGORITHM=HS256` 配置项

### Fixed - 2026-07-22 (中优先级技术债务修复 TD-04~09)

- `backend/app/api/v1/marketplace.py` GET 端点添加 `get_optional_user` 认证 (TD-04)
- `backend/app/services/retrieval/multimodal_embedder.py` 同步接口使用 `asyncio.run()` 保留语义嵌入 (TD-05)
- `backend/app/services/governance/compression.py` 低效 `len()` 改为 `func.count()` (TD-06)
- `backend/app/services/retrieval/matcher.py` SQL 拼接改为条件列表一次构建 (TD-07)
- `backend/app/core/config.py` 新增 `node_url`/`node_id` 配置项 (TD-08)
- `backend/app/api/v1/federation.py` 从 `settings` 读取节点配置 (TD-08)
- `backend/app/models/federation_peer.py` 新增 `FederationPeer` 模型 (TD-09)
- `backend/alembic/versions/0015_federation_peers.py` 新增迁移创建 `federation_peers` 表 (TD-09)
- `backend/app/services/federation/federation_service.py` 节点信息持久化到数据库 (TD-09)

### Fixed - 2026-07-22 (高优先级技术债务修复 TD-01/02/03)

- `backend/pyproject.toml` 添加 `openai>=1.0,<2.0` 依赖 (TD-03)
- `backend/requirements.txt` openai 添加版本上限 `<2.0`
- `docker-compose.prod.yml` 移除硬编码 SECRET_KEY 和数据库密码，改用 `.env.production` (TD-01)
- `docker-compose.prod.yml` POSTGRES_PASSWORD 设为必填 `${POSTGRES_PASSWORD:?...}`
- `.env.production.example` 新增生产环境配置模板
- `backend/tests/unit/test_auth_api.py` 新增 12 个测试 (TD-02)
- `backend/tests/unit/test_agents_api.py` 新增 10 个测试 (TD-02)
- `backend/tests/unit/test_admin_api.py` 新增 15 个测试 (TD-02)

### Fixed + Verified - 2026-07-21 (代码审查 28 问题修复 + 竞态/所有权测试)

#### Critical 修复 (5)
- `backend/app/models/human_expression.py` Vector(1536) -> Vector(1024) 与迁移 0014 一致
- `backend/app/core/config.py` embedding_dimension 默认值 1536 -> 1024
- `frontend/lib/api-client.ts` 搜索 API 从 GET 改为 POST + JSON body
- `backend/app/api/v1/experiences.py` update/delete/add_relation 添加 `get_current_user` 认证
- `backend/app/api/v1/evaluation.py` evaluate/create_review 添加认证 + 移除双重 commit + reviewer_id 改用 current_user.id
- `docker-compose.prod.yml` Celery 路径修正 + SECRET_KEY + DATABASE_URL + APP_ENV

#### High 修复 (5)
- `backend/app/api/v1/streaming.py` SSE 流添加 `visibility == "public"` 过滤
- `backend/app/services/marketplace/marketplace_service.py` purchase 添加 `with_for_update()` 行级锁 + create_listing 所有权验证
- `docker-compose.prod.yml` 添加 SECRET_KEY + POSTGRES_HOST + DATABASE_URL + APP_DEBUG=false
- `docker-compose.yml` DATABASE_URL 改为环境变量引用

#### Medium 修复 (11)
- `backend/app/services/retrieval/priority_chain.py` 4 处 except Exception 添加 logger.warning
- `backend/app/services/llm/provider.py` except Exception 添加 logger.warning

#### 新增测试 (7 个, 611/611 通过)
- `backend/tests/unit/test_marketplace.py` TestCreateListingOwnership: 3 个所有权验证测试
- `backend/tests/unit/test_marketplace.py` TestPurchaseRaceCondition: 3 个竞态条件测试 + 1 个下架测试
- 市场服务覆盖率: 92% (竞态+所有权分支 100% 覆盖)

### Fixed + Verified - 2026-07-21 (火山引擎集成 + Embedding 修复)

#### 火山引擎 Coding Plan 集成
- `backend/app/core/config.py` 新增 `openai_base_url` 配置项，支持 OpenAI 兼容 API
- `backend/app/services/retrieval/embedder.py` 使用配置的 base_url，支持 `dimensions` 降维参数
- `backend/app/services/llm/provider.py` LLM client 支持 base_url
- `.env.example` 添加火山引擎 Coding Plan 配置示例（doubao-embedding-vision, 1024维）
- `backend/alembic/versions/0014_change_embedding_dim.py` 迁移：vector(1536) -> vector(1024)
- `backend/scripts/regenerate_embeddings.py` 10,041 条经验 embedding 全部重新生成（0 失败）
- 搜索精度从 0.000 (HashEmbedder) 提升到 0.712 (doubao-embedding-vision)

#### Bug 修复
- `backend/app/api/v1/experiences.py` `create_experience` 添加 `get_optional_user` 依赖 + 修复 `OpenAIEmbedder` 无 `embed_async` 方法导致新经验缺 embedding
- `backend/aevum/adapters/crewai.py` + `langgraph.py` 修复 `steps: list[str]` 不兼容后端 `list[dict]` 导致 422 错误
- bcrypt 4.1+ 兼容性问题（降级到 <4.1）

#### 验证脚本
- `backend/scripts/verify_adapter_loop.py` Agent 适配器闭环验证（3/3 通过）
- `backend/scripts/verify_e2e_user_flow.py` 端到端用户流程验证（9/9 通过）
- `backend/scripts/test_search_precision.py` 搜索精度验证（0.712 语义匹配）
- `backend/scripts/check_embeddings.py` embedding 状态检查

### Fixed + Verified - 2026-07-20 (安全修复 + 适配器闭环验证)

#### 安全修复
- `backend/app/api/v1/governance.py` 新增 `_assert_experience_accessible` 权限校验函数
- fork/improve/cite 三个端点添加 visibility 权限校验（private/community/public）
- `backend/tests/unit/test_governance_visibility.py` 13 个权限单元测试

#### Bug 修复
- `backend/aevum/adapters/crewai.py` + `langgraph.py` 修复 `steps: list[str]` 不兼容后端 `list[dict]` 导致 422 错误
- `backend/app/api/v1/experiences.py` `create_experience` 添加 `get_optional_user` 依赖，修复经验 `user_id` 未设置导致 fork 自己的 private 经验返回 403

#### 验证脚本
- `backend/scripts/verify_adapter_loop.py` Agent 适配器闭环验证（3/3 通过：CrewAI + LangGraph + Generic）
- `backend/scripts/verify_e2e_user_flow.py` 端到端用户流程验证（9/9 通过：visibility 隔离 + fork 权限 + 跨用户共享）

#### 文档清理
- `.gitignore` 添加 `.deps/` 规则，清理误提交的依赖目录

### Added - 2026-07-17 (M5: 生态系统 - 经验市场 + 联邦网络)

#### 经验市场
- `backend/app/models/marketplace.py` ExperienceListing + Transaction 模型
- `backend/alembic/versions/0012_marketplace.py` 迁移 0012
- `backend/app/services/marketplace/marketplace_service.py` MarketplaceService
- `backend/app/api/v1/marketplace.py` 7 个 API 端点 (上架/浏览/购买/下架/我的购买/我的销售)
- 25 个单元测试

#### 联邦经验网络
- `backend/app/services/federation/federation_service.py` FederationService (对等节点注册/同步/联邦搜索)
- `backend/app/api/v1/federation.py` 4 个 API 端点
- 19 个单元测试

#### 人机共创工作流
- `backend/app/models/cocreation.py` CoCreationSession 模型
- `backend/alembic/versions/0013_cocreation.py` 迁移 0013
- `backend/app/api/v1/cocreation.py` 5 个 API 端点 (创建/探索/评审/列表)
- 20 个单元测试

### Vision 100% Complete - 2026-07-17
所有 16 项愿景终态验收标准全部达成。项目从基础设施到生态系统完整实现。

### Added - 2026-07-17 (M4: 高级能力 - 多模态 + 实时流)

#### 代码经验支持
- `backend/app/services/retrieval/code_embedder.py` CodeEmbedder: 64维代码特征向量, 支持Python/JS/Java/Go
- `backend/app/services/retrieval/code_search.py` CodeSearchService: 代码经验索引与检索
- 23 个单元测试

#### 多模态 Embedding
- `backend/app/services/retrieval/multimodal_embedder.py` MultimodalEmbedder: 可插拔Provider设计(local/openai)
- 统一接口 embed(content, modality) 支持 text/code/image/audio
- `backend/app/services/retrieval/embedder.py` 扩展 get_multimodal_embedder() 工厂
- 26 个单元测试

#### 实时经验流
- `backend/app/api/v1/streaming.py` SSE 流式端点: GET /stream/experiences, GET /stream/domain/{domain}
- 2秒轮询, SSE格式推送, 支持领域过滤
- 20 个单元测试

### Added - 2026-07-17 (M3: 经验生命周期管理)

#### 经验压缩与遗忘
- `backend/app/services/governance/compression.py` CompressionManager: compress/forget/auto_cleanup/find_redundant
- governance API: POST compress, POST forget, POST cleanup (admin)
- 23 个单元测试

#### 经验安全审计
- `backend/app/models/audit_log.py` AuditLog 模型
- `backend/alembic/versions/0009_audit_logs.py` 迁移 0009
- `backend/app/services/governance/audit.py` AuditLogger: log/get_logs/get_actor_logs
- governance API: GET audit trail
- 15 个单元测试

#### Agent 身份与经验归属
- `backend/alembic/versions/0010_agent_did.py` 迁移 0010 (agents.did + experiences.owner_agent_id/status/compressed)
- `backend/app/services/governance/identity.py` IdentityManager: generate_did/assign_ownership/verify_ownership
- 21 个单元测试

#### 人机协同评估
- `backend/app/models/evaluation.py` HumanReview 模型
- `backend/alembic/versions/0011_human_reviews.py` 迁移 0011
- `backend/app/services/evaluation/human_review.py` HumanReviewService
- evaluation API: POST human-review, GET reviews, GET pending-reviews
- 25 个单元测试

### Added - 2026-07-17 (M2: Agent 原生 OS - 框架适配器扩展)

#### CrewAI 适配器
- `backend/aevum/adapters/crewai.py` AevumCrewWrapper: 包裹 CrewAI Crew，自动检索+存储经验
- `backend/tests/unit/test_crewai_adapter.py` 14 个单元测试

#### 通用 REST 适配器
- `backend/aevum/adapters/generic.py` AevumHook + AevumContext: 框架无关钩子，任何框架可用
- `backend/tests/unit/test_generic_adapter.py` 15 个单元测试

#### SDK 打包
- `backend/aevum/pyproject.toml` pip installable 包配置 (v0.2.0)
- `backend/aevum/README.md` SDK 文档（安装/快速开始/三适配器示例/API参考）

### Added - 2026-07-16 (M1: 短期演进 - 检索精度 + 工作流库)

#### 检索精度优化
- `backend/app/core/config.py` 新增 7 个权重配置项（weight_context_similarity 等）
- `backend/app/services/retrieval/ranker.py` 从 Settings 读取权重，支持环境变量覆盖
- `backend/app/services/retrieval/metrics.py`（新建）4 个 IR 质量指标：precision@k, recall@k, MRR, NDCG
- `backend/tests/unit/test_retrieval_metrics.py` 22 个测试

#### 工作流库
- `backend/app/models/workflow_template.py` WorkflowTemplate ORM 模型
- `backend/app/schemas/workflow_template.py` Pydantic schemas (Create/Update/Response/List)
- `backend/alembic/versions/0008_workflow_templates.py` 迁移 0008
- `backend/app/services/experience/workflow_repository.py` CRUD repository
- `backend/app/api/v1/workflows.py` 5 个 API 端点
- `backend/app/services/bootstrap/workflow_seeds.py` 10 个种子工作流模板
- `backend/tests/unit/test_workflow_template.py` 24 个测试

### Added - 2026-07-16 (LangGraph 适配器)

#### LangGraph Agent 框架接入
- `backend/aevum/adapters/langgraph.py` AevumRunner: 包裹 LangGraph 编译图，自动检索+存储经验
  - invoke(): 执行前搜索 Aevum, 注入经验到 state, 执行后自动存储新经验
  - ainvoke(): 异步版本
  - with_experience_context(): 节点级装饰器，细粒度控制
- `backend/aevum/demo_langgraph.py` 3 个真实任务场景演示
  - Docker 部署 Python 应用 (devops)
  - 编写 pytest 单元测试 (testing)
  - 调试 Python TypeError (debugging)
  - 验证结果: 场景3置信度 0.45->0.88 (+0.43), 失败项 3->0
- `backend/tests/unit/test_langgraph_adapter.py` 10 个单元测试

### Added - 2026-07-16 (文档闭环 + 三层保障)

#### 三层文档同步保障机制
- `Autonomous_Project_Execution_Charter.md` 第 5.1 节: 闭环检查清单（5 项强制确认）
- `.trae/documents/PROJECT_STATE.md` 恢复指令: 启动前文档同步检查（git log 对比）
- `.trae/rules.md` 项目规则文件: Trae IDE 自动加载，对话启动协议 + 闭环清单
- `.trae/documents/TASKS.md` 全面重写: Phase 0-9 全部标记已完成，长期愿景列入"未规划"
- `.trae/documents/TEST_REPORT.md` 更新: 测试数 275->290，新增 SDK/GEG/端到端验证条目

### Added - 2026-07-15 (CI/CD 流水线)

#### GitHub Actions CI
- `.github/workflows/ci.yml` CI 流水线（lint/pytest/build/type-check/前端test）
- 非阻塞设计: lint/type-check/build 失败不阻塞测试运行
- 数据库迁移步骤: CI 中自动运行 alembic upgrade head
- 前端 Test --ci 标志: 非交互模式运行
- CI/CD 验证通过: 所有验收标准全部达标

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
  - `app/services/governance/versioning.py` VersioningManager（经验版本/谱系追踪）
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
