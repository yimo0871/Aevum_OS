# Aevum（薪火）OS - 总体路线图

---

## 路线图概览

```
Phase 0: 项目初始化          [✅ 完成]
    └── Phase 1: 核心数据层    [⏳ 下一步]
         ├── Phase 2: 执行层
         │    └── Phase 3: 检索层
         │         └── Phase 4: 评估层
         │              └── Phase 5: 前端 Dashboard
         │                   └── Phase 6: 集成部署
         │                        └── Phase 7: 冷启动
         └── (前端骨架可并行)
```

---

## 关键路径

Phase 0 → 1 → 2 → 3 → 4 → 6 → 7

---

## 各阶段详情

### Phase 0: 项目初始化 ✅
- Git 仓库初始化
- 后端骨架（FastAPI + SQLAlchemy + 配置）
- 前端骨架（Next.js + TypeScript + Tailwind）
- Docker 开发环境
- 项目状态文件

### Phase 1: 核心数据层 ⏳
- Experience 数据模型（ORM + Pydantic Schema）
- PostgreSQL Schema + pgvector 扩展
- Alembic 数据库迁移
- 经验 CRUD API
- 图谱关系管理
- 单元测试

### Phase 2: Agent 执行层
- 任务执行引擎
- 8 步经验流水线编排
- 工具调用抽象
- 收敛控制系统
- Celery 异步任务
- 执行追踪记录

### Phase 3: 检索层
- 向量相似度匹配
- 匹配评分函数（6因子）
- 四级优先级链
- pgvector HNSW 索引
- 检索 API

### Phase 4: 评估层
- 任务评估器
- 经验评估器
- 工作流评估器
- 七个系统级指标
- "无评估=无效输出" 强制规则

### Phase 5: 前端 Dashboard
- 基础布局与导航
- Dashboard 总览页（指标卡片）
- 经验管理页（列表/详情/图谱可视化）
- 任务执行页（8步流水线进度）
- 指标监控页（时序图表）

### Phase 6: 集成测试与部署
- 端到端集成测试
- CI/CD 流水线
- Docker 生产配置
- 性能测试
- 安全检查
- 部署文档

### Phase 7: 冷启动与 Bootstrap
- 种子数据生成脚本
- 10,000 条种子经验
- 评估系统初始化
- 冷启动验证
