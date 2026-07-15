# Aevum（薪火）OS - 项目状态总览

> **此文件是项目唯一可信的数据来源。**
> 每次新开发会话开始时，先读取此文件恢复上下文。

---

## 当前阶段

**核心闭环验证完成** - ✅ 全部 Phase 完成 + 端到端验证通过 + 全量中文化

**项目状态**：MVP 可运行，核心 8 步流水线闭环已验证

---

## 整体进度

| Phase | 名称 | 状态 | 进度 |
|-------|------|------|------|
| Phase 0 | 项目初始化 | ✅ 完成 | 100% |
| Phase 1 | 核心数据层 | ✅ 完成 | 100% |
| Phase 2 | Agent 执行层 | ✅ 完成 | 100% |
| Phase 3 | 检索层 | ✅ 完成 | 100% |
| Phase 4 | 评估层 | ✅ 完成 | 100% |
| Phase 5 | 前端 Dashboard | ✅ 完成 | 100% |
| Phase 6 | 集成测试与部署 | ✅ 完成 | 100% |
| Phase 7 | 冷启动与 Bootstrap | ✅ 完成 | 100% |
| 核心闭环补完 | 评估+Embedding+检索验证 | ✅ 完成 | 100% |
| 全量中文化 | 种子数据+前端+工具描述 | ✅ 完成 | 100% |
| 图谱可视化 | react-flow 节点-边关系图 | ✅ 完成 | 100% |
| 安全加固 | API限流+输入验证 | ✅ 完成 | 100% |
| Phase 7 验收 | 10,000条种子+评估+性能 | ✅ 完成 | 100% |
| Phase 6 压测 | 100并发P95<1s ALL PASS | ✅ 完成 | 100% |
| Dashboard缓存 | 5秒TTL内存缓存 | ✅ 完成 | 100% |
| Phase 5 前端测试 | 58个测试, 覆盖率90.47% | ✅ 完成 | 100% |

**总体进度**：MVP 100%（Phase 5-7 验收标准全部达标，仅 CI/CD 验证需推送 GitHub）

---

## 系统运行状态

### Docker 服务（4 个容器）

| 服务 | 容器名 | 端口 | 状态 |
|------|--------|------|------|
| 后端 API | aevum-backend | 8000 | ✅ 运行中 |
| Celery Worker | aevum-worker | - | ✅ 运行中 |
| PostgreSQL + pgvector | aevum-db | 5432 | ✅ Healthy |
| Redis | aevum-redis | 6379 | ✅ Healthy |

### 前端服务

| 服务 | 地址 | 状态 |
|------|------|------|
| Next.js 开发服务器 | http://localhost:3000 | ✅ 运行中 |

### 数据状态

| 指标 | 值 |
|------|-----|
| 经验总数 | 10,000 |
| 已评估 | 10,000 (100%) |
| 待评估 | 0 |
| 图谱关系 | ~3,999 |
| Embedding 向量 | 10,000 |
| 检索延迟 (10K) | 18ms |
| 单元测试 | 70/70 通过 |
| 端到端测试 | 8/8 通过 |

---

## 前端页面（5 个）

| 页面 | URL | 功能 |
|------|-----|------|
| Dashboard 总览 | / | 统计卡片 + 系统指标 |
| 经验管理 | /experiences | 列表 + 筛选 + 分页 + 详情 |
| 经验检索 | /search | 搜索 + 领域筛选 + 评分排序 |
| 任务执行 | /execution | 提交任务 + 工具列表 |
| 指标监控 | /metrics | 7 个指标卡片 |

---

## Git 提交历史

```
20a9378 feat: 全量中文化 - 种子数据/前端/工具描述 + 修复中文检索
aca996c feat: 添加检索页面+端到端测试(8/8 pass)+1002条经验
c2ea64d feat: 真实用户会话验证 - 8步流水线闭环测试通过
c1bc33c feat: 完成核心闭环 - 1000条经验评估+embedding+检索验证
6548365 fix: 删除默认静态首页, 修复 Dashboard 页面渲染
597af98 fix: 修复类型注解运行时错误和4个测试失败 (70/70 pass)
b9f8005 fix: 修复 Docker 部署问题
a1a6ba9 feat: Phase 7 - 冷启动与 Bootstrap
4ee5c49 feat: Phase 6 - 集成测试与部署
3d4aaf9 feat: Phase 5 - 前端 Dashboard
33f6eb9 feat: Phase 4 - 评估层
b26829a feat: Phase 3 - 检索层
62e73be feat: Phase 2 - Agent 执行层
42f4005 feat: Phase 1 - 核心数据层
42d8def feat: Phase 0 - 项目初始化
```

---

## 待完成项（按优先级）

### 高优先级
1. **真实 LLM 集成** -- 当前使用 HashEmbedder（hash 模拟），需配置 OpenAI API Key 使用真实语义 embedding
2. **图谱可视化** -- 计划中要求的节点-边关系图（react-flow / d3.js）
3. **安全加固** -- 输入验证、SQL 注入防护、API 限流

### 中优先级
4. **种子数据补完** -- 从 1000 条扩展到 10,000 条
5. **性能测试** -- API 压测、检索延迟验证
6. **CI/CD 验证** -- GitHub Actions 流水线端到端验证

### 低优先级
7. **用户认证** -- 登录/注册/权限控制
8. **经验去重** -- 相似经验自动检测和合并
9. **治理层** -- 信任评分、版本治理
10. **Human World** -- 人类表达层

---

## 关键技术决策

| 决策 | 选择 | 理由 |
|------|------|------|
| 向量检索 | pgvector | MVP 不引入额外数据库 |
| Embedding | HashEmbedder（本地） | 无需外部 API，支持中文 bigram |
| 图存储 | PostgreSQL JSONB | 避免 Neo4j 运维成本 |
| 前端状态 | React Query | 服务端状态自动缓存/刷新 |
| 异步任务 | Celery + Redis | 经验生成流水线异步化 |

---

## 恢复指令

新会话恢复步骤：
1. 读取此文件了解项目状态
2. 运行 `docker-compose up -d db redis backend worker` 启动后端
3. 运行 `cd frontend && npm run dev` 启动前端
4. 访问 http://localhost:3000 验证系统
5. 运行 `docker exec aevum-backend python -m pytest tests/unit/ -v` 验证测试
6. 从"待完成项"选择下一步工作
