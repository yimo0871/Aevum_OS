"""Seed data for WorkflowTemplate - 10 standard workflow templates."""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_template import WorkflowTemplate

logger = logging.getLogger(__name__)


SEED_TEMPLATES = [
    {
        "name": "Docker 部署 Python 应用",
        "description": "使用 Docker 容器化部署 Python FastAPI 应用的标准工作流，包含镜像构建、推送和部署。",
        "domain": "devops",
        "task_type": "deployment",
        "steps": [
            {"name": "构建镜像", "action": "docker build -t app:latest .", "description": "使用多阶段构建减小镜像体积"},
            {"name": "本地测试", "action": "docker run --rm app:latest pytest", "description": "在容器内运行测试套件"},
            {"name": "标签推送", "action": "docker tag app:latest registry/app:v1.0 && docker push", "description": "推送到镜像仓库"},
            {"name": "部署上线", "action": "kubectl apply -f k8s/", "description": "应用 Kubernetes 部署配置"},
            {"name": "健康检查", "action": "curl /health", "description": "验证服务健康状态"},
        ],
        "tools": ["docker", "docker-compose", "kubectl", "pytest"],
        "expected_outcome": {
            "success_criteria": "服务正常运行且健康检查通过",
            "metrics": {"deploy_time_s": 120, "image_size_mb": 85},
            "artifacts": ["container_image", "k8s_manifests"],
        },
    },
    {
        "name": "编写 pytest 单元测试",
        "description": "为 Python 模块编写全面的单元测试，确保覆盖核心逻辑路径和边界条件。",
        "domain": "testing",
        "task_type": "unit_test",
        "steps": [
            {"name": "分析代码", "action": "阅读目标模块接口和逻辑", "description": "理解输入输出和边界条件"},
            {"name": "编写测试用例", "action": "创建 test_module.py", "description": "覆盖正常路径、边界和异常场景"},
            {"name": "运行测试", "action": "pytest tests/ -v", "description": "执行全部测试并查看结果"},
            {"name": "检查覆盖率", "action": "pytest --cov=app --cov-report=term-missing", "description": "确保覆盖率达标"},
            {"name": "修复失败用例", "action": "调试并修复失败的测试", "description": "分析失败原因并修复"},
        ],
        "tools": ["pytest", "coverage", "pytest-mock", "pytest-asyncio"],
        "expected_outcome": {
            "success_criteria": "所有测试通过且覆盖率 >= 80%",
            "metrics": {"coverage_pct": 85, "test_count": 20},
            "artifacts": ["test_report", "coverage_report"],
        },
    },
    {
        "name": "调试 TypeError 错误",
        "description": "系统化排查和修复 Python TypeError 异常，从复现到根因分析再到修复验证。",
        "domain": "debugging",
        "task_type": "debug",
        "steps": [
            {"name": "复现错误", "action": "运行触发 TypeError 的代码", "description": "确认错误可稳定复现"},
            {"name": "阅读 traceback", "action": "分析堆栈追踪信息", "description": "定位出错文件和行号"},
            {"name": "检查类型", "action": "在出错处添加 type() 调试输出", "description": "确认实际类型与预期不符"},
            {"name": "修复代码", "action": "添加类型转换或参数校验", "description": "确保类型正确"},
            {"name": "验证修复", "action": "重新运行测试", "description": "确认错误已消除"},
        ],
        "tools": ["pdb", "pytest", "mypy"],
        "expected_outcome": {
            "success_criteria": "TypeError 已消除，所有测试通过",
            "metrics": {"debug_time_min": 15, "regression_count": 0},
            "artifacts": ["fix_patch"],
        },
    },
    {
        "name": "代码审查 checklist",
        "description": "按照标准化 checklist 进行代码审查，覆盖逻辑、风格、安全和性能维度。",
        "domain": "development",
        "task_type": "code_review",
        "steps": [
            {"name": "通读代码", "action": "理解 PR 的整体变更意图", "description": "把握上下文和影响范围"},
            {"name": "检查代码风格", "action": "运行 pylint/flake8", "description": "确保符合 PEP 8 规范"},
            {"name": "检查逻辑正确性", "action": "审查核心业务逻辑", "description": "验证边界条件和异常处理"},
            {"name": "检查安全性", "action": "审查输入校验和权限控制", "description": "识别潜在安全漏洞"},
            {"name": "提供反馈", "action": "撰写审查意见", "description": "给出具体的改进建议"},
        ],
        "tools": ["pylint", "mypy", "git", "bandit"],
        "expected_outcome": {
            "success_criteria": "审查完成，所有问题已记录",
            "metrics": {"issues_found": 5, "critical_count": 0},
            "artifacts": ["review_report"],
        },
    },
    {
        "name": "数据库迁移执行",
        "description": "安全执行 SQLAlchemy/Alembic 数据库迁移，包含备份、验证和回滚方案。",
        "domain": "devops",
        "task_type": "migration",
        "steps": [
            {"name": "备份数据库", "action": "pg_dump > backup.sql", "description": "迁移前完整备份"},
            {"name": "生成迁移", "action": "alembic revision --autogenerate -m 'desc'", "description": "自动生成迁移脚本"},
            {"name": "审查迁移", "action": "检查 upgrade/downgrade 函数", "description": "确认迁移逻辑正确"},
            {"name": "执行迁移", "action": "alembic upgrade head", "description": "应用到目标数据库"},
            {"name": "验证结果", "action": "检查表结构和数据", "description": "确认迁移成功"},
        ],
        "tools": ["alembic", "psql", "pg_dump"],
        "expected_outcome": {
            "success_criteria": "迁移成功应用，数据完整无损",
            "metrics": {"migration_time_s": 30, "data_loss": 0},
            "artifacts": ["migration_script", "backup_file"],
        },
    },
    {
        "name": "API 性能优化",
        "description": "识别 API 性能瓶颈并进行优化，从 profiling 到优化实施再到效果验证。",
        "domain": "development",
        "task_type": "optimization",
        "steps": [
            {"name": "性能分析", "action": "使用 py-spy 生成火焰图", "description": "定位耗时函数"},
            {"name": "识别瓶颈", "action": "分析 N+1 查询和慢查询", "description": "找出主要性能问题"},
            {"name": "实施优化", "action": "添加缓存/优化查询/异步化", "description": "针对性优化瓶颈"},
            {"name": "基准测试", "action": "使用 locust 压测对比", "description": "量化优化效果"},
            {"name": "验证结果", "action": "确认响应时间下降", "description": "确保优化达标"},
        ],
        "tools": ["py-spy", "locust", "redis", "sqlalchemy"],
        "expected_outcome": {
            "success_criteria": "API 响应时间降低 50% 以上",
            "metrics": {"latency_p99_ms": 100, "throughput_rps": 500},
            "artifacts": ["flamegraph", "benchmark_report"],
        },
    },
    {
        "name": "安全漏洞扫描",
        "description": "对项目进行全方位安全扫描，覆盖依赖漏洞、代码漏洞和配置风险。",
        "domain": "security",
        "task_type": "audit",
        "steps": [
            {"name": "扫描依赖", "action": "safety check", "description": "检查已知漏洞的依赖包"},
            {"name": "扫描代码", "action": "bandit -r app/", "description": "静态分析代码安全漏洞"},
            {"name": "扫描配置", "action": "检查密钥泄露和配置风险", "description": "审查环境变量和配置文件"},
            {"name": "分析发现", "action": "按严重程度分类", "description": "评估每个漏洞的影响"},
            {"name": "修复建议", "action": "生成修复方案", "description": "提供具体的修复步骤"},
        ],
        "tools": ["bandit", "safety", "semgrep", "trufflehog"],
        "expected_outcome": {
            "success_criteria": "所有高危漏洞已识别并修复",
            "metrics": {"high_severity": 0, "medium_severity": 3},
            "artifacts": ["security_report", "fix_recommendations"],
        },
    },
    {
        "name": "日志分析排障",
        "description": "通过分析系统日志定位和排查生产环境问题，从日志收集到根因定位。",
        "domain": "debugging",
        "task_type": "log_analysis",
        "steps": [
            {"name": "收集日志", "action": "从 ELK/CloudWatch 拉取日志", "description": "按时间范围筛选"},
            {"name": "过滤异常", "action": "grep ERROR/WARN/Traceback", "description": "提取错误级别日志"},
            {"name": "关联分析", "action": "按 request_id/trace_id 关联", "description": "重建请求链路"},
            {"name": "定位根因", "action": "分析异常堆栈和上下文", "description": "确定根本原因"},
            {"name": "文档记录", "action": "撰写排障报告", "description": "记录问题和解决方案"},
        ],
        "tools": ["grep", "jq", "elasticsearch", "kibana"],
        "expected_outcome": {
            "success_criteria": "根因已定位，修复方案已实施",
            "metrics": {"analysis_time_min": 30, "similar_issues": 2},
            "artifacts": ["incident_report", "log_evidence"],
        },
    },
    {
        "name": "CI/CD 流水线配置",
        "description": "配置 GitHub Actions CI/CD 流水线，实现代码推送后自动构建、测试和部署。",
        "domain": "devops",
        "task_type": "cicd",
        "steps": [
            {"name": "定义流水线", "action": "创建 .github/workflows/ci.yml", "description": "设计 CI/CD 阶段"},
            {"name": "配置构建", "action": "设置 Docker 构建步骤", "description": "构建并缓存镜像"},
            {"name": "配置测试", "action": "添加 pytest 运行步骤", "description": "运行单元和集成测试"},
            {"name": "配置部署", "action": "添加自动部署到 staging", "description": "合并到 main 后自动部署"},
            {"name": "配置通知", "action": "添加失败通知", "description": "Slack/邮件通知构建结果"},
        ],
        "tools": ["github-actions", "docker", "kubectl", "pytest"],
        "expected_outcome": {
            "success_criteria": "流水线正常运行，推送后自动部署",
            "metrics": {"pipeline_time_min": 8, "failure_rate": 0},
            "artifacts": ["ci_config", "deployment_log"],
        },
    },
    {
        "name": "文档生成",
        "description": "从代码 docstring 和 OpenAPI 规范自动生成项目文档，包含 API 参考和使用示例。",
        "domain": "development",
        "task_type": "documentation",
        "steps": [
            {"name": "提取 docstring", "action": "扫描所有模块的文档字符串", "description": "收集 API 文档信息"},
            {"name": "生成 API 文档", "action": "导出 OpenAPI JSON", "description": "从 FastAPI 自动生成"},
            {"name": "编写示例", "action": "为每个 API 编写使用示例", "description": "包含请求和响应示例"},
            {"name": "构建文档站", "action": "mkdocs build", "description": "生成静态文档网站"},
            {"name": "审查发布", "action": "检查文档完整性并发布", "description": "确保文档准确无误"},
        ],
        "tools": ["sphinx", "mkdocs", "openapi-generator"],
        "expected_outcome": {
            "success_criteria": "文档站点生成，API 参考完整",
            "metrics": {"api_docs_count": 50, "examples_count": 30},
            "artifacts": ["docs_site", "api_reference"],
        },
    },
]


async def seed_workflow_templates(session: AsyncSession) -> int:
    """插入 10 个标准工作流模板种子数据.

    如果同名模板已存在则跳过，保证幂等性。

    Args:
        session: 异步数据库会话

    Returns:
        新插入的模板数量
    """
    inserted = 0
    for seed in SEED_TEMPLATES:
        # 检查是否已存在同名模板
        existing = await session.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.name == seed["name"])
        )
        if existing.scalar_one_or_none() is not None:
            logger.info("跳过已存在的模板: %s", seed["name"])
            continue

        template = WorkflowTemplate(
            name=seed["name"],
            description=seed["description"],
            domain=seed["domain"],
            task_type=seed["task_type"],
            steps=seed["steps"],
            tools=seed["tools"],
            expected_outcome=seed["expected_outcome"],
            visibility="public",
        )
        session.add(template)
        inserted += 1
        logger.info("插入模板: %s", seed["name"])

    await session.commit()
    logger.info("种子数据完成: 新增 %d 个工作流模板", inserted)
    return inserted
