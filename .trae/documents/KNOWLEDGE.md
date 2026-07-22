# Aevum（薪火）OS - 知识沉淀

---

## 设计原则

### 人机分离四原则（不可违反）

1. **人类数据绝不直接进入经验图谱**
2. **Agent 不得改写人类表达**
3. **人类输出仅供观察性使用**
4. **Agent 输出必须完全结构化且可评估**

### 跨世界桥接（仅允许四种）

- Inspiration Link（灵感链接）
- Observation Link（观察链接）
- Recommendation Link（推荐链接）
- Optional Reflection Link（可选反思链接）
- **不允许直接合并 Schema，仅允许语义引用**

### 核心原则

- **无评估 = 无效输出** - 任何未经过评估环节的输出，系统不予承认
- **未生成 Experience = 任务无效**

---

## 技术注意事项

### PostgreSQL + pgvector

- 使用 `pgvector/pgvector:pg16` Docker 镜像（内置 pgvector 扩展）
- embedding 维度：1536（对应 `text-embedding-3-small`）
- 索引类型：HNSW（比 IVFFlat 更适合增量插入）

### SQLAlchemy 异步

- 使用 `asyncpg` 驱动（不是 `psycopg2`）
- `async_sessionmaker` 创建会话工厂
- `expire_on_commit=False` 避免异步访问过期对象

### FastAPI

- 使用 `lifespan` 替代 `on_event`（后者已弃用）
- CORS 中间件必须在前端端口（3000）配置
- OpenAPI 文档自动生成在 `/docs`

### Next.js

- App Router 使用路由组 `(dashboard)` 实现布局共享
- `output: 'standalone'` 用于 Docker 多阶段构建
- Server Components 默认，客户端组件需 `"use client"` 指令

---

## 踩坑记录

（持续更新）

---

## 最佳实践

（持续更新）

---

## 未来优化方向

1. 向量检索迁移到 Qdrant/Milvus（当数据量超过 100 万）
2. 图存储迁移到 Neo4j（当图查询复杂度增加）
3. 多租户支持（当前为单租户）
4. 联邦经验网络（隐私保护下的跨组织共享）
5. 经验压缩与遗忘机制（防止图谱膨胀）
