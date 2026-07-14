# Aevum（薪火）OS - 变更日志

---

## [Unreleased]

### Added - 2026-07-14 (Phase 0)

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
