# Aevum（薪火）OS - 项目状态总览

> **此文件是项目唯一可信的数据来源。**
> 每次新开发会话开始时，先读取此文件恢复上下文。

---

## 当前阶段

**Phase 2：Agent 执行层（Agent Execution Layer）** - ✅ 已完成

**下一阶段**：Phase 3 - 检索层（Retrieval & Inference Layer）

---

## 整体进度

| Phase | 名称 | 状态 | 进度 |
|-------|------|------|------|
| Phase 0 | 项目初始化 | ✅ 完成 | 100% |
| Phase 1 | 核心数据层（Experience Layer） | ✅ 完成 | 100% |
| Phase 2 | Agent 执行层 | ⏳ 待开始 | 0% |
| Phase 3 | 检索层 | ⏳ 待开始 | 0% |
| Phase 4 | 评估层 | ⏳ 待开始 | 0% |
| Phase 5 | 前端 Dashboard | ⏳ 待开始 | 0% |
| Phase 6 | 集成测试与部署 | ⏳ 待开始 | 0% |
| Phase 7 | 冷启动与 Bootstrap | ⏳ 待开始 | 0% |

**总体进度**：~37%（Phase 0 + 1 + 2 完成）

---

## 当前阻塞项

无。

---

## 关键文件索引

| 文件 | 用途 |
|------|------|
| `.trae/documents/PROJECT_STATE.md` | 本文件 - 项目状态总览 |
| `.trae/documents/ROADMAP.md` | 总体路线图 |
| `.trae/documents/MILESTONES.md` | 里程碑与验收标准 |
| `.trae/documents/TASKS.md` | 任务看板 |
| `.trae/documents/DECISIONS.md` | 架构决策记录 |
| `.trae/documents/CHANGELOG.md` | 变更日志 |
| `.trae/documents/RISKS.md` | 风险登记 |
| `.trae/documents/TEST_REPORT.md` | 测试报告 |
| `.trae/documents/ARCHITECTURE.md` | 技术架构文档 |
| `.trae/documents/KNOWLEDGE.md` | 知识沉淀 |

---

## 技术栈

- **后端**：Python 3.12 + FastAPI + SQLAlchemy + PostgreSQL(pgvector) + Redis + Celery
- **前端**：Next.js + React 19 + TypeScript + Tailwind CSS
- **部署**：Docker + Docker Compose
- **CI/CD**：GitHub Actions（待配置）

---

## 最近更新

- 2026-07-14: Phase 2 完成 - Agent 执行层（工具调用、追踪记录、收敛控制、执行引擎、8步流水线、Celery异步、API路由、测试）
- 2026-07-14: Phase 1 完成 - Experience 数据层（ORM模型、Schema、Alembic迁移、pgvector、CRUD API、图谱关系、经验工厂、单元测试）
- 2026-07-14: Phase 0 完成 - 项目初始化、后端/前端骨架、Docker 环境、项目状态文件
