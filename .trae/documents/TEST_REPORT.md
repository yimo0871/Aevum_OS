# Aevum（薪火）OS - 测试报告

---

## 当前状态

**全部 Phase 完成** - 前端已验证通过，后端待运行时验证。

---

## 测试框架

| 层面 | 工具 | 配置状态 |
|------|------|----------|
| 后端单元测试 | pytest + pytest-asyncio | ✅ 已配置（pyproject.toml） |
| 后端覆盖率 | pytest-cov | ✅ 已配置 |
| 前端类型检查 | tsc --noEmit | ✅ 已配置 |
| 前端构建 | next build | ✅ 已配置 |
| E2E 测试 | pytest + httpx ASGITransport | ✅ 已编写 |
| 性能测试 | locust / k6 | ⏳ 待配置 |

---

## 验证结果

### 前端验证（2026-07-14）

| 测试项 | 结果 | 详情 |
|--------|------|------|
| TypeScript 类型检查 | ✅ 通过 | `tsc --noEmit` 零错误 |
| 前端构建 | ✅ 通过 | 7 页面全部生成（Static: 6, Dynamic: 1） |
| 页面路由 | ✅ 通过 | /, /execution, /experiences, /experiences/[id], /metrics |
| 修复 TS2339 | ✅ 修复 | metricConfig 属性统一（inverse/suffix） |

### 后端验证（2026-07-14）

| 测试项 | 结果 | 详情 |
|--------|------|------|
| 导入链完整性 | ✅ 通过 | 所有 `from app.*` 导入路径正确 |
| 模块结构 | ✅ 通过 | 4层服务（execution/experience/retrieval/evaluation）完整 |
| API 路由注册 | ✅ 通过 | 4组路由（experiences/execution/retrieval/evaluation）已注册 |
| ORM 模型一致性 | ✅ 通过 | Experience/ExperienceRelation/ExecutionTrace/Evaluation/SystemMetric |
| IDE 诊断 | ✅ 通过 | 无诊断错误 |
| Docker 构建 | ⚠️ 待验证 | Docker Desktop 未运行 |
| pytest 单元测试 | ⚠️ 待验证 | Python 未安装，需通过 Docker 运行 |

### 后端测试文件清单

| 文件 | 测试内容 | 测试用例数 |
|------|----------|-----------|
| `tests/unit/test_schemas.py` | Pydantic Schema 验证 | 15+ |
| `tests/unit/test_factory.py` | ExperienceFactory | 4 |
| `tests/unit/test_tools.py` | 工具注册/调用 | 6 |
| `tests/unit/test_convergence.py` | 收敛控制 | 7 |
| `tests/unit/test_engine.py` | 执行引擎/追踪器 | 7 |
| `tests/unit/test_retrieval.py` | 向量化/匹配/排序 | 12 |
| `tests/unit/test_evaluation.py` | 任务/经验评估 | 12 |
| `tests/e2e/test_pipeline_e2e.py` | 8步流水线/生命周期/人机分离 | 8 |
| `tests/e2e/test_api_health.py` | API 路由/输入验证 | 9 |
| `tests/integration/test_experiences_api.py` | API 端点集成 | 6 |

**总计**: 80+ 测试用例

---

## 运行测试指南

### 前端测试
```bash
cd frontend
npx tsc --noEmit        # 类型检查
npm run build            # 构建
```

### 后端测试（需要 Docker Desktop 运行）
```bash
# 通过 Docker
docker-compose up -d db redis
docker-compose exec backend pytest -v --cov=app

# 或本地运行（需要 Python 3.12+）
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
pytest -v --cov=app
```

---

## 覆盖率目标

| Phase | 后端覆盖率 | 前端覆盖率 | 状态 |
|-------|-----------|-----------|------|
| Phase 1 | ≥ 80% | - | ✅ 测试已编写 |
| Phase 2 | ≥ 80% | - | ✅ 测试已编写 |
| Phase 3 | ≥ 80% | - | ✅ 测试已编写 |
| Phase 4 | ≥ 80% | - | ✅ 测试已编写 |
| Phase 5 | ≥ 80% | ≥ 70% | ✅ 构建验证通过 |
| Phase 6 | ≥ 80% | ≥ 70% | ✅ E2E 测试已编写 |
