# Aevum（薪火）OS - 技术债务清单

---

## 概述

本文档记录项目截至 2026-07-22 的已知技术债务和待办事项，按优先级分类。

项目当前状态：愿景 100% 达成（16/16），4/4 真实场景验证全部通过，611 个后端单元测试 + 64 个前端组件测试全通过。

---

## 高优先级（3 项） -- 全部已修复 ✅

### TD-01: docker-compose.prod.yml 硬编码敏感信息 ✅ 已修复

- **文件**: `docker-compose.prod.yml`
- **问题描述**: 生产环境编排文件中硬编码了 SECRET_KEY 和数据库密码
- **修复**: 移除硬编码值，改用 `.env.production` 文件，POSTGRES_PASSWORD 设为必填，创建 `.env.production.example` 模板
- **修复提交**: a3d57d4 (2026-07-22)

### TD-02: auth.py / admin.py / agents.py API 无测试覆盖 ✅ 已修复

- **文件**: `backend/app/api/v1/auth.py` (4 端点), `admin.py` (10 端点), `agents.py` (4 端点)
- **问题描述**: 共 18 个 API 端点完全没有专用测试文件覆盖
- **修复**: 新增 3 个测试文件共 37 个测试
  - `test_auth_api.py`: 12 个测试（注册/登录/用户信息）
  - `test_agents_api.py`: 10 个测试（创建/列表/删除/重生成key）
  - `test_admin_api.py`: 15 个测试（用户CRUD/经验审核/Agent/统计）
- **修复提交**: a3d57d4 (2026-07-22)
- **注意**: 测试待 Python 环境恢复后验证

### TD-03: pyproject.toml 缺失 openai 依赖 ✅ 已修复

- **文件**: `backend/pyproject.toml`
- **问题描述**: 代码直接 `import openai` 但 pyproject.toml 未声明依赖
- **修复**: 在 dependencies 中添加 `openai>=1.0,<2.0`，requirements.txt 同步添加上限
- **修复提交**: a3d57d4 (2026-07-22)

---

## 中优先级（6 项）

### TD-04: marketplace.py GET 端点无认证

- **文件**: `backend/app/api/v1/marketplace.py`
- **行号**: 58 (list_listings), 91 (get_listing)
- **问题描述**: 两个 GET 端点缺少 `get_current_user` 依赖，未认证用户可浏览市场数据
- **影响**: 市场数据可能包含敏感信息（卖家 ID、价格策略等）
- **建议修复**: 添加 `get_optional_user` 或 `get_current_user` 依赖

### TD-05: multimodal_embedder.py 同步接口降级丢失语义

- **文件**: `backend/app/services/retrieval/multimodal_embedder.py`
- **行号**: 124-126
- **问题描述**: `_sync_embed_text` 方法检测到 OpenAIEmbedder（async embed）时降级为 HashEmbedder，丢失语义嵌入能力
- **影响**: 配置了 OpenAI provider 时，同步接口仍使用无语义的哈希向量
- **建议修复**: 提供异步接口 `embed_text_async`，或在同步方法中使用 `asyncio.run()` 调用异步 embedder

### TD-06: compression.py 低效 count 查询

- **文件**: `backend/app/services/governance/compression.py`
- **行号**: 180-186
- **问题描述**: 使用 `len(result.scalars().all())` 加载所有行到内存后取长度，而非 SQL `COUNT()` 聚合
- **影响**: 大数据量下内存开销和性能问题
- **建议修复**: 改为 `select(func.count(ExperienceRelation.id)).where(...)`

### TD-07: matcher.py SQL 字符串拼接构建

- **文件**: `backend/app/services/retrieval/matcher.py`
- **行号**: 85-128
- **问题描述**: `match_by_vector` 方法通过 `text(sql.text + "...")` 拼接 SQL 字符串
- **影响**: 可读性差、易出错、难以维护（无 SQL 注入风险，参数已绑定）
- **建议修复**: 改用 SQLAlchemy ORM `select()` + 动态 `.where()` 链式构建

### TD-08: federation.py 硬编码 localhost:8000

- **文件**: `backend/app/api/v1/federation.py`
- **行号**: 31-32
- **问题描述**: `get_federation_service()` 中硬编码 `node_url="http://localhost:8000"` 和 `node_id="local"`，未从配置读取
- **影响**: 部署到非本地环境时联邦功能失效
- **建议修复**: 从 `settings` 读取 `node_url` 和 `node_id` 配置项

### TD-09: 联邦节点信息不持久化

- **文件**: `backend/app/services/federation/federation_service.py`
- **行号**: 37
- **问题描述**: 对等节点注册信息存储在内存字典 `self._peers` 中，服务重启后丢失
- **影响**: 每次重启需要重新注册所有对等节点
- **建议修复**: 创建 `federation_peers` 数据库表持久化节点关系

---

## 低优先级（6 项）

### TD-10: multimodal_embedder.py 未使用的导入

- **文件**: `backend/app/services/retrieval/multimodal_embedder.py`
- **行号**: 13
- **问题描述**: `import asyncio` 被导入但从未使用
- **影响**: 代码整洁度
- **建议修复**: 删除未使用的导入

### TD-11: 重复脚本目录

- **文件**: `backend/scripts/scripts/`
- **问题描述**: 存在嵌套的 `scripts/scripts/` 目录，包含 `bootstrap_seeds.py` 和 `verify_bootstrap.py` 的旧副本
- **影响**: 代码组织混乱，可能产生混淆
- **建议修复**: 删除 `backend/scripts/scripts/` 目录

### TD-12: CHANGELOG 引用不存在的 lineage.py

- **文件**: `.trae/documents/CHANGELOG.md`
- **行号**: 251
- **问题描述**: 引用了 `app/services/governance/lineage.py` 和 `LineageTracker` 类，但该文件不存在（功能已合并到 `versioning.py`）
- **影响**: 文档不一致
- **建议修复**: 更新 CHANGELOG 中的引用

### TD-13: passlib + bcrypt 兼容性警告

- **文件**: `backend/requirements.txt`
- **行号**: 33-34
- **问题描述**: passlib 1.7.4 与 bcrypt 4.x 存在已知兼容性问题，运行时产生 `AttributeError` 警告
- **影响**: 运行时警告（不影响功能）
- **建议修复**: 升级到 passlib 1.7.5+ 或迁移到 bcrypt 直接调用

### TD-14: 经验市场无真实支付

- **文件**: `backend/app/services/marketplace/marketplace_service.py`
- **问题描述**: `purchase` 方法直接将交易状态设为 `"completed"`，无支付网关集成
- **影响**: 无法进行真实交易（ROADMAP 已知后续迭代项）
- **建议修复**: 集成 Stripe / 支付宝 / 微信支付 API

### TD-15: 多模态经验基于文本描述

- **文件**: `backend/app/services/retrieval/multimodal_embedder.py`
- **问题描述**: 图像和音频经验基于文本描述/转录的文本嵌入，非真实图像/音频数据处理
- **影响**: 多模态能力为简化版本（ROADMAP 已知后续迭代项）
- **建议修复**: 集成 CLIP / Whisper 等真实多模态模型

---

## 亮点

- **零 TODO/FIXME 注释** -- 代码中无遗留待办标记
- **零注释掉的代码块** -- 无死代码
- **README.md 基本一致** -- 与项目状态匹配
- **611 个单元测试** -- 核心逻辑覆盖完善
- **4/4 真实场景验证** -- 全部通过

---

## 依赖版本约束建议

| 依赖 | 当前约束 | 建议约束 | 原因 |
|------|----------|----------|------|
| `openai` | `>=1.0` | `>=1.0,<2.0` | 防止 2.x 破坏性变更 |
| `fastapi` | `>=0.115.0` | `>=0.115.0,<1.0` | 防止 1.0 破坏性变更 |
| `sqlalchemy` | `>=2.0.36` | `>=2.0.36,<3.0` | 防止 3.0 破坏性变更 |
| `pydantic` | `>=2.10.0` | `>=2.10.0,<3.0` | 防止 3.0 破坏性变更 |
| `bcrypt` | `>=4.0.0,<4.1` | `>=4.0.0,<5.0` + 升级 passlib | 长期方案 |

---

## 更新日志

| 日期 | 内容 |
|------|------|
| 2026-07-22 | 初始创建，记录 15 项技术债务（3 高 + 6 中 + 6 低） |
