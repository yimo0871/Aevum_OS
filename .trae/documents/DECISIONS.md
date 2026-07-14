# Aevum（薪火）OS - 架构决策记录（ADR）

---

## ADR-001: 技术栈选择

**日期**：2026-07-14
**状态**：已采纳

### 背景

项目从零开始，需要选择前后端技术栈。核心需求：
- AI/LLM 生态兼容性
- 类型安全
- 高性能异步
- 快速开发

### 决策

- **后端**：Python 3.12 + FastAPI + SQLAlchemy(async) + PostgreSQL + Redis + Celery
- **前端**：Next.js + React 19 + TypeScript + Tailwind CSS

### 理由

- Python 是 AI/LLM 生态最成熟的语言
- FastAPI 提供高性能异步、自动 OpenAPI 文档、类型安全
- Next.js 提供 SSR/SSG、App Router、文件系统路由
- TypeScript strict mode 减少运行时错误
- Tailwind CSS + shadcn/ui 提供高质量设计

### 影响

- 后端开发需要 Python 3.12+
- 前端开发需要 Node.js 20+
- 部署需要 Docker 环境

---

## ADR-002: 向量检索方案

**日期**：2026-07-14
**状态**：已采纳

### 背景

经验检索需要向量相似度匹配。可选方案：pgvector、Qdrant、Milvus、Pinecone。

### 决策

MVP 阶段使用 **pgvector**（PostgreSQL 扩展）。

### 理由

- 不引入额外数据库，降低运维复杂度
- PostgreSQL 已是核心依赖，pgvector 是自然扩展
- MVP 数据规模（10万条）下性能足够
- 后期可迁移到专用向量数据库

### 影响

- 需要使用 `pgvector/pgvector` Docker 镜像
- 检索接口需要抽象化，便于后期迁移

---

## ADR-003: 图存储方案

**日期**：2026-07-14
**状态**：已采纳

### 背景

经验图谱需要图存储。可选方案：Neo4j、PostgreSQL JSONB + 关系表。

### 决策

MVP 阶段使用 **PostgreSQL JSONB + 关系表** 模拟图关系。

### 理由

- 避免 Neo4j 运维成本
- MVP 阶段图查询复杂度不高
- JSONB + 关系表可以覆盖基本图操作
- 迁移到 Neo4j 的路径清晰

### 影响

- 复杂图查询（多跳遍历）性能有限
- 需要设计 ExperienceRelation 表结构

---

## ADR-004: MVP 层级范围

**日期**：2026-07-14
**状态**：已采纳

### 背景

六层架构全部实现工程量巨大，需要确定 MVP 范围。

### 决策

MVP 实现 **4 层核心闭环**：
- Agent Execution Layer（完整）
- Experience Layer（完整）
- Retrieval & Inference Layer（完整）
- Evaluation Layer（完整）

暂缓：
- Human Expression Layer（简化为用户输入接口）
- Governance & Evolution Layer（仅版本控制 + 基本信任评分）

### 理由

4 层核心闭环覆盖完整的 8 步经验流水线，验证核心价值。
人机分离原则保留，但完整表达层非核心闭环必需。

### 影响

- 第一版不支持完整的人类非结构化表达存储
- 第一版不支持 fork/merge/decay 等高级治理功能
