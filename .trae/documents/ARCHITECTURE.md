# Aevum（薪火）OS - 技术架构文档

---

## 1. 系统架构

### 1.1 六层架构（来自设计蓝图）

```
┌─────────────────────────────────────┐
│  6. Governance & Evolution Layer    │  ← 治理与演进（MVP: 简化）
├─────────────────────────────────────┤
│  5. Evaluation Layer                │  ← 评估（MVP: 完整）
├─────────────────────────────────────┤
│  4. Retrieval & Inference Layer     │  ← 检索与推理（MVP: 完整）
├─────────────────────────────────────┤
│  3. Experience Layer                │  ← 经验（核心）（MVP: 完整）
├─────────────────────────────────────┤
│  2. Agent Execution Layer           │  ← Agent 执行（MVP: 完整）
├─────────────────────────────────────┤
│  1. Human Expression Layer          │  ← 人类表达（MVP: 简化）
└─────────────────────────────────────┘
```

### 1.2 技术架构

```
┌──────────────────────────────────────────────┐
│                 Frontend                      │
│  Next.js 16 + React 19 + TypeScript          │
│  Tailwind CSS + shadcn/ui                    │
│  Port: 3000                                  │
├──────────────────────────────────────────────┤
│                 Nginx (prod)                  │
│  Reverse Proxy + Load Balancer               │
├──────────────────────────────────────────────┤
│                 Backend API                   │
│  FastAPI + Uvicorn (dev) / Gunicorn (prod)   │
│  Port: 8000                                  │
├──────────────┬───────────────┬───────────────┤
│  PostgreSQL  │    Redis      │   Celery      │
│  + pgvector  │  (cache/queue)│   Worker      │
│  Port: 5432  │  Port: 6379   │               │
└──────────────┴───────────────┴───────────────┘
```

---

## 2. 数据模型

### 2.1 Experience 对象（核心）

```python
Experience = {
    id: UUID,
    timestamp: datetime,
    context: {
        domain: str,
        task_type: str,
        constraints: dict
    },
    intent: str,
    execution: {
        steps: list,
        tools: list[str],
        trace: dict
    },
    outcome: {
        success: bool,
        metrics: dict
    },
    reflection: {
        what_worked: list[str],
        what_failed: list[str],
        why: str
    },
    reusable_patterns: list,
    confidence_score: float,
    provenance: {
        human_signals: list,
        agent_signals: list,
        external_sources: list
    },
    version: int,
    embedding: vector(1536)  # pgvector, for retrieval
}
```

### 2.2 ExperienceRelation（图谱边）

```python
ExperienceRelation = {
    id: UUID,
    source_id: UUID,       # Experience FK
    target_id: UUID,       # Experience FK
    relation_type: enum,   # reuse | citation | fork | improvement | dependency
    weight: float,
    created_at: datetime
}
```

### 2.3 ExecutionTrace（执行追踪）

```python
ExecutionTrace = {
    id: UUID,
    experience_id: UUID,   # Experience FK
    steps: list,           # JSONB
    tools: list,           # JSONB
    trace: dict,           # JSONB
    duration: float,       # seconds
    status: enum           # pending | running | completed | failed
}
```

---

## 3. 8 步经验流水线

```
Step 1: retrieve_similar_experiences  → 检索层
Step 2: select_best_workflows         → 检索层
Step 3: execute_task                  → 执行层
Step 4: record_full_trace             → 执行层
Step 5: generate_experience_object    → 经验层（工厂）
Step 6: evaluate_experience           → 评估层
Step 7: store_into_graph              → 经验层（存储）
Step 8: update_reuse_index            → 检索层

失败条件：未生成 Experience → 任务标记无效
```

---

## 4. 检索优先级链

```
Priority 1: 用户自身经验图谱    ← 最优先
Priority 2: 社区经验图谱
Priority 3: 全球经验图谱
Priority 4: 外部网络数据         ← 仅兜底
```

匹配评分函数：
```
score = f(
    context_similarity,    # 向量余弦相似度
    success_rate,          # 历史成功率
    reuse_count,           # 复用次数
    domain_distance,       # 领域距离
    recency,               # 时效性
    confidence             # 置信度
)
```

---

## 5. 收敛控制

| 控制规则 | 限制 |
|----------|------|
| Experience Engine 最大迭代 | 3 次 |
| Workflow Engine 最大迭代 | 2 次 |
| Evaluation Engine 最大迭代 | 2 次 |
| Retrieval Engine 最大迭代 | 2 次 |
| 改进阈值 | Δ performance ≥ ε |
| 停滞检测 | 连续 2 次无改进 → 冻结 → 回滚 |

---

## 6. 项目目录结构

```
aevum/
├── backend/           # Python FastAPI 后端
│   ├── app/
│   │   ├── main.py
│   │   ├── core/      # config, database
│   │   ├── api/v1/    # REST API 路由
│   │   ├── models/    # SQLAlchemy ORM
│   │   ├── schemas/   # Pydantic 模型
│   │   ├── services/  # 业务逻辑
│   │   │   ├── execution/    # Agent 执行层
│   │   │   ├── experience/   # 经验层
│   │   │   ├── retrieval/    # 检索层
│   │   │   └── evaluation/   # 评估层
│   │   └── utils/
│   ├── tests/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # Next.js 前端
│   ├── app/
│   │   ├── (dashboard)/     # Dashboard 页面组
│   │   └── layout.tsx
│   ├── lib/           # 工具库
│   ├── types/         # TypeScript 类型
│   └── Dockerfile
├── docker-compose.yml # 开发环境
├── docker-compose.prod.yml
└── .trae/documents/   # 项目状态文件
```
