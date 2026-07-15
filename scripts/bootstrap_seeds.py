"""Bootstrap seed data generator - 种子经验数据生成.

生成 10,000 条合成经验数据，用于系统冷启动。
数据覆盖多个领域和任务类型，模拟真实 Agent 执行经验。

Usage:
    # 生成 JSON 文件（不依赖数据库）
    python scripts/bootstrap_seeds.py --output seeds.json --count 10000

    # 通过 API 导入（需要后端运行）
    python scripts/bootstrap_seeds.py --api http://localhost:8000 --count 10000

    # 直接导入数据库（需要数据库运行）
    python scripts/bootstrap_seeds.py --db --count 10000

    # 指定数据源（synthetic/datasets/templates/expert/mixed）
    python scripts/bootstrap_seeds.py --source mixed --count 1000
    python scripts/bootstrap_seeds.py --source expert --count 500
"""

import argparse
import asyncio
import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path


# ── 数据模板 ──

DOMAINS = ["后端开发", "前端开发", "运维部署", "数据处理", "测试质量", "安全审计", "机器学习", "综合通用"]

TASK_TYPES = {
    "后端开发": ["API设计", "数据库迁移", "身份认证", "缓存优化", "错误处理"],
    "前端开发": ["UI组件", "页面布局", "状态管理", "性能优化", "无障碍适配"],
    "运维部署": ["部署上线", "CI/CD流水线", "基础设施", "监控告警", "容器化"],
    "数据处理": ["ETL管道", "数据清洗", "数据分析", "数据可视化", "模型训练"],
    "测试质量": ["单元测试", "集成测试", "端到端测试", "压力测试", "安全测试"],
    "安全审计": ["漏洞扫描", "权限审计", "加密实现", "渗透测试", "合规检查"],
    "机器学习": ["模型训练", "特征工程", "模型评估", "模型部署", "超参优化"],
    "综合通用": ["文档编写", "代码重构", "代码审查", "方案规划", "技术调研"],
}

INTENTS = {
    "部署上线": [
        "使用{tool}将{app}部署到{env}环境",
        "为{app}搭建{tool}自动化部署流水线到{env}",
        "配置{tool}实现{app}零停机部署",
    ],
    "CI/CD流水线": [
        "使用{tool}为{app}创建CI/CD流水线",
        "使用{tool}自动化{app}的测试和部署流程",
        "为{app}搭建{tool}持续集成工作流",
    ],
    "单元测试": [
        "使用{tool}为{app}编写单元测试",
        "使用{tool}为{app}实现{coverage}%测试覆盖率",
        "为{app}搭建{tool}测试框架",
    ],
    "API设计": [
        "使用{tool}为{app}设计RESTful API",
        "使用{tool}实现{app}的CRUD接口",
        "使用{tool}为{app}创建GraphQL Schema",
    ],
    "模型训练": [
        "使用{tool}在{dataset}上训练{model}模型",
        "使用{tool}为{task}微调{model}",
        "使用{tool}在{dataset}上评估{model}性能",
    ],
}

TOOLS = ["Docker容器", "Kubernetes编排", "Git版本控制", "Pytest测试", "Jest测试",
         "Nginx反代", "Redis缓存", "PostgreSQL数据库", "MongoDB文档库", "Elasticsearch搜索引擎",
         "Grafana监控", "Prometheus采集", "Terraform基础设施", "Ansible自动化",
         "Jenkins流水线", "GitHub Actions", "React框架", "Vue框架", "FastAPI框架",
         "Django框架", "Flask框架", "LangChain链式调用", "OpenAI API", "Pandas数据处理",
         "NumPy数值计算", "Scikit-learn机器学习", "PyTorch深度学习", "TensorFlow深度学习"]

APPS = ["用户服务", "认证服务", "支付接口", "数据看板", "移动应用",
        "数据管道", "AI模型", "通知服务", "搜索引擎", "分析平台"]

ENVS = ["生产环境", "预发布环境", "开发环境", "测试环境"]
MODELS = ["BERT", "GPT", "ResNet", "YOLO", "LLaMA", "Transformer"]
DATASETS = ["MNIST", "CIFAR-10", "ImageNet", "COCO", "维基百科", "Common Crawl"]
TASKS = ["分类任务", "检测任务", "生成任务", "摘要任务", "翻译任务"]
COVERAGE = ["80", "85", "90", "95", "100"]


def generate_intent(domain: str, task_type: str) -> str:
    """Generate a realistic intent string."""
    templates = INTENTS.get(task_type, [
        f"在{domain}领域执行{task_type}任务",
        f"在{domain}上下文中进行{task_type}",
    ])
    template = random.choice(templates)
    return template.format(
        app=random.choice(APPS),
        env=random.choice(ENVS),
        tool=random.choice(TOOLS),
        model=random.choice(MODELS),
        dataset=random.choice(DATASETS),
        task=random.choice(TASKS),
        coverage=random.choice(COVERAGE),
    )


def generate_experience(index: int) -> dict:
    """Generate a single Experience object."""
    domain = random.choice(DOMAINS)
    task_type = random.choice(TASK_TYPES[domain])
    success = random.random() > 0.25  # 75% success rate
    days_ago = random.randint(0, 90)
    timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

    tools_used = random.sample(TOOLS, random.randint(1, 5))
    step_count = random.randint(2, 8)
    steps = [
        {"action": f"step_{i}", "status": "completed" if success or i < step_count - 1 else "failed"}
        for i in range(step_count)
    ]

    what_worked = []
    what_failed = []
    if success:
        what_worked = random.sample([
            "标准模式应用成功", "工具配置正确", "环境验证通过",
            "预检查通过", "回滚方案就绪", "监控已启用",
        ], random.randint(1, 3))
    else:
        what_failed = random.sample([
            "端口冲突", "权限不足", "超时", "依赖缺失",
            "配置错误", "网络不可达", "资源超限",
        ], random.randint(1, 2))
        what_worked = random.sample([
            "初始设置已完成", "失败前部分执行",
        ], random.randint(0, 1))

    confidence = random.uniform(0.3, 0.95) if success else random.uniform(0.1, 0.5)

    patterns_count = random.randint(0, 3)
    reusable_patterns = [
        {"pattern": f"模式_{i}", "applicable": True, "domain": domain}
        for i in range(patterns_count)
    ]

    return {
        "id": str(uuid.uuid4()),
        "timestamp": timestamp.isoformat(),
        "context": {
            "domain": domain,
            "task_type": task_type,
            "constraints": {
                "env": random.choice(ENVS),
                "timeout": random.choice([30, 60, 120, 300]),
                "resource_limit": random.choice(["低", "中", "高"]),
            },
        },
        "intent": generate_intent(domain, task_type),
        "execution": {
            "steps": steps,
            "tools": tools_used,
            "trace": {
                "duration_ms": random.randint(1000, 120000),
                "commands_run": random.randint(3, 20),
                "files_modified": random.randint(0, 10),
            },
        },
        "outcome": {
            "success": success,
            "metrics": {
                "execution_time_s": random.uniform(1.0, 120.0),
                "resource_usage_mb": random.randint(50, 2048),
                "error_count": 0 if success else random.randint(1, 5),
            },
        },
        "reflection": {
            "what_worked": what_worked,
            "what_failed": what_failed,
            "why": "标准执行流程" if success else "配置异常导致失败",
        },
        "reusable_patterns": reusable_patterns,
        "confidence_score": round(confidence, 4),
        "provenance": {
            "human_signals": [],
            "agent_signals": [
                {"agent_id": f"agent-{random.randint(1, 10)}", "contribution": "execution"}
            ],
            "external_sources": [],
        },
        "version": 1,
        "evaluation_status": "pending",
        "created_at": timestamp.isoformat(),
        "updated_at": timestamp.isoformat(),
    }


# ── 开放数据集场景 ──

OPEN_DATASET_SCENARIOS = [
    {
        "domain": "前端开发",
        "task_type": "UI组件",
        "intent": "使用 React 开发可复用的表格组件，支持排序、分页和自定义渲染",
        "steps": ["设计组件接口", "实现基础表格", "添加排序功能", "集成分页控件", "支持自定义单元格渲染"],
        "tools": ["React框架", "Jest测试", "Git版本控制"],
        "what_worked": ["组件设计清晰", "Props 接口合理", "单元测试覆盖核心逻辑"],
        "what_failed": [],
        "why": "采用受控组件模式，通过 props 传递数据和回调，组件可复用性高",
    },
    {
        "domain": "后端开发",
        "task_type": "API设计",
        "intent": "使用 Django REST Framework 构建博客系统的 RESTful API",
        "steps": ["设计数据模型", "创建序列化器", "实现视图集", "配置路由", "添加权限控制", "编写 API 测试"],
        "tools": ["Django框架", "PostgreSQL数据库", "Redis缓存"],
        "what_worked": ["ViewSet 减少重复代码", "序列化器验证完善", "权限分层清晰"],
        "what_failed": [],
        "why": "DRF 的 ViewSet 配合 Router 大幅简化了 CRUD 接口开发",
    },
    {
        "domain": "运维部署",
        "task_type": "容器化",
        "intent": "使用 Kubernetes 部署微服务应用，含自动扩缩容和滚动更新",
        "steps": ["编写 Dockerfile", "创建 K8s Deployment", "配置 Service", "设置 HPA 自动扩缩容", "配置滚动更新策略"],
        "tools": ["Docker容器", "Kubernetes编排", "Grafana监控", "Prometheus采集"],
        "what_worked": ["多阶段构建减小镜像体积", "HPA 配置合理", "就绪探针避免流量打到未就绪 Pod"],
        "what_failed": [],
        "why": "合理配置资源请求和限制，HPA 根据 CPU 使用率自动扩缩容",
    },
    {
        "domain": "后端开发",
        "task_type": "缓存优化",
        "intent": "优化 PostgreSQL 慢查询，为高频读取接口添加 Redis 缓存层",
        "steps": ["分析慢查询日志", "添加数据库索引", "实现 Redis 缓存", "设置缓存失效策略", "压测验证效果"],
        "tools": ["PostgreSQL数据库", "Redis缓存", "Grafana监控"],
        "what_worked": ["复合索引加速 JOIN 查询", "缓存命中率提升至 95%", "旁路缓存模式简单可靠"],
        "what_failed": ["首次缓存穿透导致短暂延迟"],
        "why": "数据库索引优化配合 Redis 旁路缓存，读延迟从 200ms 降至 10ms",
    },
    {
        "domain": "后端开发",
        "task_type": "缓存优化",
        "intent": "设计 Redis 缓存策略，解决缓存穿透、击穿和雪崩问题",
        "steps": ["分析缓存问题场景", "实现布隆过滤器防穿透", "添加互斥锁防击穿", "设置随机过期时间防雪崩", "监控缓存指标"],
        "tools": ["Redis缓存", "FastAPI框架"],
        "what_worked": ["布隆过滤器有效拦截无效请求", "互斥锁避免重复回源", "随机 TTL 防止集中失效"],
        "what_failed": [],
        "why": "三层防护策略系统性地解决了缓存的三大经典问题",
    },
    {
        "domain": "前端开发",
        "task_type": "状态管理",
        "intent": "使用 Vue 3 + Pinia 构建 SPA 应用的状态管理架构",
        "steps": ["设计 Store 结构", "实现用户模块", "实现购物车模块", "添加持久化插件", "集成 DevTools"],
        "tools": ["Vue框架", "Git版本控制"],
        "what_worked": ["模块化 Store 解耦清晰", "组合式 API 提升可维护性", "持久化方案可靠"],
        "what_failed": [],
        "why": "Pinia 的组合式 Store 写法相比 Vuex 更简洁，TypeScript 支持更好",
    },
    {
        "domain": "数据处理",
        "task_type": "ETL管道",
        "intent": "构建 Elasticsearch 全文搜索索引管道，支持中文分词",
        "steps": ["设计索引 Mapping", "配置 IK 中文分词器", "实现数据同步管道", "优化搜索相关性", "压测搜索性能"],
        "tools": ["Elasticsearch搜索引擎", "Redis缓存"],
        "what_worked": ["IK 分词器中文效果优秀", "Bulk API 批量写入高效", "高亮搜索结果提升体验"],
        "what_failed": ["索引重建期间搜索结果不完整"],
        "why": "合理设计 Mapping 和分词策略，搜索响应时间控制在 50ms 以内",
    },
    {
        "domain": "后端开发",
        "task_type": "API设计",
        "intent": "设计 GraphQL API 替代 RESTful 接口，支持灵活查询和类型安全",
        "steps": ["定义 GraphQL Schema", "实现 Resolver", "添加 DataLoader 批量加载", "配置查询复杂度限制", "集成 Apollo Studio"],
        "tools": ["FastAPI框架", "PostgreSQL数据库"],
        "what_worked": ["客户端按需查询减少过度获取", "DataLoader 解决 N+1 问题", "类型系统提升开发效率"],
        "what_failed": ["查询复杂度限制初期设置过低"],
        "why": "GraphQL 的灵活查询能力适合多端复用，DataLoader 是解决 N+1 的关键",
    },
    {
        "domain": "运维部署",
        "task_type": "容器化",
        "intent": "使用 Docker 多阶段构建优化 Node.js 应用镜像体积",
        "steps": ["分析原始镜像大小", "设计多阶段构建流程", "使用 Alpine 基础镜像", "利用构建缓存层", "验证运行时依赖"],
        "tools": ["Docker容器", "Nginx反代"],
        "what_worked": ["镜像体积从 1.2GB 减至 180MB", "构建缓存利用率高", "生产镜像不含 devDependencies"],
        "what_failed": [],
        "why": "多阶段构建分离构建环境和运行环境，Alpine 基础镜像进一步减小体积",
    },
    {
        "domain": "机器学习",
        "task_type": "模型部署",
        "intent": "使用 TorchServe 部署 BERT 模型，提供推理 API 服务",
        "steps": ["导出模型为 TorchScript", "编写自定义 Handler", "配置模型配置文件", "启动推理服务", "压测推理延迟"],
        "tools": ["PyTorch深度学习", "Docker容器", "Prometheus采集"],
        "what_worked": ["TorchScript 加速推理", "批量推理提升吞吐量", "Prometheus 指标可观测"],
        "what_failed": ["GPU 内存溢出需调优 batch size"],
        "why": "TorchServe 提供了标准化的模型部署流程，配合 TorchScript 提升推理性能",
    },
]


def generate_from_open_datasets(count: int) -> list[dict]:
    """生成基于常见开源项目场景的经验."""
    experiences = []
    for i in range(count):
        scenario = random.choice(OPEN_DATASET_SCENARIOS)
        success = random.random() > 0.2
        days_ago = random.randint(0, 90)
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        steps = [
            {"action": s, "status": "completed" if success or j < len(scenario["steps"]) - 1 else "failed"}
            for j, s in enumerate(scenario["steps"])
        ]

        what_worked = scenario["what_worked"] if success else scenario["what_worked"][:1]
        what_failed = scenario["what_failed"] if not success else []
        why = scenario["why"] if success else f"执行中遇到问题: {scenario['what_failed'][0] if scenario['what_failed'] else '未知错误'}"

        confidence = random.uniform(0.6, 0.85) if success else random.uniform(0.3, 0.5)

        experiences.append({
            "id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "context": {
                "domain": scenario["domain"],
                "task_type": scenario["task_type"],
                "constraints": {
                    "env": random.choice(ENVS),
                    "timeout": random.choice([30, 60, 120]),
                    "resource_limit": random.choice(["低", "中", "高"]),
                },
            },
            "intent": scenario["intent"],
            "execution": {
                "steps": steps,
                "tools": scenario["tools"],
                "trace": {
                    "duration_ms": random.randint(5000, 60000),
                    "commands_run": random.randint(5, 15),
                    "files_modified": random.randint(2, 8),
                },
            },
            "outcome": {
                "success": success,
                "metrics": {
                    "execution_time_s": random.uniform(5.0, 60.0),
                    "resource_usage_mb": random.randint(100, 1024),
                    "error_count": 0 if success else random.randint(1, 3),
                },
            },
            "reflection": {
                "what_worked": what_worked,
                "what_failed": what_failed,
                "why": why,
            },
            "reusable_patterns": [
                {"pattern": f"场景模式_{scenario['task_type']}", "applicable": True, "domain": scenario["domain"]}
            ],
            "confidence_score": round(confidence, 4),
            "provenance": {
                "human_signals": [],
                "agent_signals": [
                    {"agent_id": f"agent-{random.randint(1, 10)}", "contribution": "execution"}
                ],
                "external_sources": [{"type": "open_dataset", "name": scenario["domain"]}],
            },
            "version": 1,
            "evaluation_status": "pending",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
        })
    return experiences


# ── 工作流模板 ──

WORKFLOW_TEMPLATES = [
    {
        "domain": "运维部署",
        "task_type": "CI/CD流水线",
        "intent": "搭建 GitHub Actions CI/CD 流水线，实现自动测试、构建和部署",
        "steps": ["配置触发条件", "编写测试 Job", "编写构建 Job", "配置部署 Job", "设置环境变量和密钥", "添加状态徽章"],
        "tools": ["GitHub Actions", "Docker容器", "Jest测试"],
        "what_worked": ["并行 Job 加速流水线", "缓存依赖减少构建时间", "密钥管理安全可靠"],
        "what_failed": [],
        "why": "GitHub Actions 的 YAML 配置直观，矩阵策略和缓存机制有效提升效率",
    },
    {
        "domain": "综合通用",
        "task_type": "代码审查",
        "intent": "建立标准化的代码审查流程，确保代码质量和知识共享",
        "steps": ["定义审查清单", "配置 PR 模板", "设置审查规则", "集成自动化检查", "建立审查文化"],
        "tools": ["Git版本控制", "GitHub Actions"],
        "what_worked": ["审查清单标准化", "自动化检查减少人工负担", "PR 模板提升描述质量"],
        "what_failed": [],
        "why": "将审查标准文档化并配合自动化工具，平衡了质量与效率",
    },
    {
        "domain": "测试质量",
        "task_type": "单元测试",
        "intent": "实施测试驱动开发（TDD）流程：红-绿-重构循环",
        "steps": ["编写失败测试", "实现最小代码使测试通过", "重构优化代码", "运行全量测试验证", "提交代码"],
        "tools": ["Pytest测试", "Git版本控制"],
        "what_worked": ["先写测试明确需求", "小步迭代降低风险", "重构阶段有测试保障"],
        "what_failed": ["初期编写测试耗时较多"],
        "why": "TDD 迫使开发者先思考接口设计，测试即文档，重构有安全网",
    },
    {
        "domain": "综合通用",
        "task_type": "方案规划",
        "intent": "实施敏捷开发流程：Sprint 计划、每日站会和回顾会议",
        "steps": ["梳理产品待办列表", "Sprint 计划会议", "每日站会同步", "Sprint 评审", "回顾会议改进"],
        "tools": ["Git版本控制"],
        "what_worked": ["短迭代快速反馈", "站会提升透明度", "回顾会议持续改进"],
        "what_failed": [],
        "why": "两周一个 Sprint 的节奏平衡了交付速度和质量，回顾会议驱动持续改进",
    },
    {
        "domain": "运维部署",
        "task_type": "CI/CD流水线",
        "intent": "设计 Git 分支策略：主干开发 + Feature Branch + Release Branch",
        "steps": ["定义分支模型", "配置分支保护规则", "制定合并策略", "设置 CI 门禁", "文档化发布流程"],
        "tools": ["Git版本控制", "GitHub Actions"],
        "what_worked": ["Feature Branch 隔离开发", "PR 审查保证质量", "Release Branch 支持热修复"],
        "what_failed": [],
        "why": "清晰的分支策略减少了合并冲突，Release Branch 支持生产环境热修复",
    },
    {
        "domain": "运维部署",
        "task_type": "监控告警",
        "intent": "建立发布管理流程：灰度发布、金丝雀部署和回滚机制",
        "steps": ["设计灰度策略", "配置金丝雀部署", "设置监控指标", "实现自动回滚", "制定发布手册"],
        "tools": ["Kubernetes编排", "Prometheus采集", "Grafana监控"],
        "what_worked": ["金丝雀部署控制爆炸半径", "自动回滚快速恢复", "监控指标驱动决策"],
        "what_failed": ["灰度比例初期设置不当"],
        "why": "渐进式发布配合自动回滚，将发布风险降至最低",
    },
    {
        "domain": "运维部署",
        "task_type": "监控告警",
        "intent": "建立事故响应流程：告警、分级、处理和复盘",
        "steps": ["定义告警级别", "配置告警通知", "建立值班制度", "制定处理 SOP", "事后复盘改进"],
        "tools": ["Grafana监控", "Prometheus采集"],
        "what_worked": ["告警分级减少噪音", "值班制度保证响应", "复盘改进形成闭环"],
        "what_failed": ["初期告警过多导致疲劳"],
        "why": "标准化的响应流程缩短了 MTTR，复盘机制确保同类问题不重复发生",
    },
    {
        "domain": "后端开发",
        "task_type": "错误处理",
        "intent": "实施 Feature Flag 机制，实现功能灰度发布和快速回滚",
        "steps": ["选择 Feature Flag 服务", "设计 Flag 命名规范", "实现 Flag 检查逻辑", "配置灰度规则", "建立 Flag 生命周期管理"],
        "tools": ["FastAPI框架", "Redis缓存"],
        "what_worked": ["无需部署即可控制功能开关", "灰度规则灵活", "快速回滚不影响其他功能"],
        "what_failed": [],
        "why": "Feature Flag 解耦了发布和部署，使功能控制更加灵活和安全",
    },
]


def generate_from_workflow_templates(count: int) -> list[dict]:
    """生成基于标准工作流的经验."""
    experiences = []
    for i in range(count):
        template = random.choice(WORKFLOW_TEMPLATES)
        success = random.random() > 0.15
        days_ago = random.randint(0, 90)
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        steps = [
            {"action": s, "status": "completed" if success or j < len(template["steps"]) - 1 else "failed"}
            for j, s in enumerate(template["steps"])
        ]

        what_worked = template["what_worked"] if success else template["what_worked"][:1]
        what_failed = template["what_failed"] if not success else []
        why = template["why"] if success else f"流程执行中遇到问题: {template['what_failed'][0] if template['what_failed'] else '协调问题'}"

        confidence = random.uniform(0.55, 0.8) if success else random.uniform(0.3, 0.5)

        experiences.append({
            "id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "context": {
                "domain": template["domain"],
                "task_type": template["task_type"],
                "constraints": {
                    "env": random.choice(ENVS),
                    "timeout": random.choice([60, 120, 300]),
                    "resource_limit": random.choice(["中", "高"]),
                },
            },
            "intent": template["intent"],
            "execution": {
                "steps": steps,
                "tools": template["tools"],
                "trace": {
                    "duration_ms": random.randint(3000, 45000),
                    "commands_run": random.randint(4, 12),
                    "files_modified": random.randint(1, 6),
                },
            },
            "outcome": {
                "success": success,
                "metrics": {
                    "execution_time_s": random.uniform(3.0, 45.0),
                    "resource_usage_mb": random.randint(50, 512),
                    "error_count": 0 if success else random.randint(1, 2),
                },
            },
            "reflection": {
                "what_worked": what_worked,
                "what_failed": what_failed,
                "why": why,
            },
            "reusable_patterns": [
                {"pattern": f"工作流模板_{template['task_type']}", "applicable": True, "domain": template["domain"]}
            ],
            "confidence_score": round(confidence, 4),
            "provenance": {
                "human_signals": [{"contributor": "workflow_team", "contribution": "process_design"}],
                "agent_signals": [
                    {"agent_id": f"agent-{random.randint(1, 10)}", "contribution": "execution"}
                ],
                "external_sources": [{"type": "workflow_template", "name": template["task_type"]}],
            },
            "version": 1,
            "evaluation_status": "pending",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
        })
    return experiences


# ── 专家模板 ──

EXPERT_TEMPLATES = [
    {
        "domain": "后端开发",
        "task_type": "缓存优化",
        "intent": "实施高并发场景下的性能优化：连接池调优、异步化和缓存策略",
        "steps": ["性能瓶颈分析", "优化数据库连接池", "将同步 I/O 改为异步", "引入多级缓存", "压测验证优化效果"],
        "tools": ["FastAPI框架", "Redis缓存", "PostgreSQL数据库", "Prometheus采集"],
        "what_worked": ["连接池参数调优减少等待", "异步 I/O 提升吞吐量", "多级缓存命中率 98%"],
        "what_failed": [],
        "why": "系统化地从连接池、异步化和缓存三个层面优化，QPS 从 500 提升至 5000",
    },
    {
        "domain": "安全审计",
        "task_type": "加密实现",
        "intent": "实施安全加固方案：HTTPS、CSRF 防护、XSS 过滤和 SQL 注入防御",
        "steps": ["配置 TLS 证书", "实现 CSRF Token", "添加 XSS 过滤中间件", "使用参数化查询", "配置安全响应头", "安全扫描验证"],
        "tools": ["Nginx反代", "FastAPI框架", "PostgreSQL数据库"],
        "what_worked": ["TLS 1.3 配置安全", "CSRF Token 有效防护", "参数化查询彻底防注入"],
        "what_failed": [],
        "why": "纵深防御策略从传输层、应用层到数据层全面加固，通过 OWASP Top 10 扫描",
    },
    {
        "domain": "综合通用",
        "task_type": "代码重构",
        "intent": "应用微服务架构设计模式：服务拆分、API 网关和服务发现",
        "steps": ["分析单体架构痛点", "定义服务边界", "设计 API 网关", "实现服务注册发现", "配置分布式链路追踪", "逐步迁移"],
        "tools": ["Kubernetes编排", "Docker容器", "Grafana监控"],
        "what_worked": ["按业务能力拆分服务", "API 网关统一入口", "服务发现自动扩缩容"],
        "what_failed": ["分布式事务处理复杂"],
        "why": "领域驱动设计指导服务拆分，API 网关模式统一了跨切面关注点",
    },
    {
        "domain": "后端开发",
        "task_type": "数据库迁移",
        "intent": "遵循数据库设计原则：规范化、索引策略和分区方案",
        "steps": ["分析数据模型", "实施第三范式", "设计复合索引", "配置表分区", "验证查询性能"],
        "tools": ["PostgreSQL数据库", "Redis缓存"],
        "what_worked": ["规范化减少数据冗余", "复合索引加速复杂查询", "按时间分区提升大表性能"],
        "what_failed": [],
        "why": "在规范化与反规范化之间取得平衡，索引策略基于实际查询模式设计",
    },
    {
        "domain": "后端开发",
        "task_type": "缓存优化",
        "intent": "实现 API 限流机制：令牌桶算法 + Redis 分布式限流",
        "steps": ["分析限流需求", "选择限流算法", "实现令牌桶限流器", "使用 Redis 实现分布式限流", "配置限流响应和告警"],
        "tools": ["Redis缓存", "FastAPI框架"],
        "what_worked": ["令牌桶支持突发流量", "Redis Lua 脚本保证原子性", "限流响应包含 Retry-After"],
        "what_failed": [],
        "why": "令牌桶算法兼顾平滑限流和突发流量，Redis 分布式实现支持多实例部署",
    },
    {
        "domain": "运维部署",
        "task_type": "监控告警",
        "intent": "实施分布式链路追踪：OpenTelemetry + Jaeger 全链路可观测",
        "steps": ["集成 OpenTelemetry SDK", "配置自动埋点", "部署 Jaeger 后端", "添加业务 Span", "设置采样策略"],
        "tools": ["Prometheus采集", "Grafana监控", "Docker容器"],
        "what_worked": ["自动埋点覆盖 HTTP/DB", "业务 Span 定位瓶颈", "采样策略平衡开销"],
        "what_failed": [],
        "why": "全链路追踪将排障时间从小时级降至分钟级，是微服务可观测性的基石",
    },
    {
        "domain": "后端开发",
        "task_type": "错误处理",
        "intent": "实现熔断器模式：防止级联故障，保障系统弹性",
        "steps": ["分析故障场景", "实现熔断器状态机", "配置失败阈值和恢复时间", "集成降级逻辑", "压测验证熔断效果"],
        "tools": ["FastAPI框架", "Redis缓存", "Prometheus采集"],
        "what_worked": ["三态机模型清晰", "半开状态自动探测恢复", "降级逻辑保证用户体验"],
        "what_failed": [],
        "why": "熔断器模式有效隔离了故障服务，防止级联失败导致系统雪崩",
    },
    {
        "domain": "后端开发",
        "task_type": "缓存优化",
        "intent": "设计缓存失效策略：主动失效 + 被动过期 + 延迟双删",
        "steps": ["分析缓存一致性需求", "实现写后主动失效", "设置合理 TTL 被动过期", "延迟双删防并发问题", "监控缓存一致性"],
        "tools": ["Redis缓存", "PostgreSQL数据库"],
        "what_worked": ["主动失效保证强一致", "TTL 兜底最终一致", "延迟双删解决并发脏读"],
        "what_failed": [],
        "why": "多层级缓存失效策略在强一致性和性能之间取得了平衡",
    },
    {
        "domain": "机器学习",
        "task_type": "模型评估",
        "intent": "实施模型蒸馏和量化，优化大模型推理性能",
        "steps": ["选择教师模型", "训练学生模型", "应用 INT8 量化", "评估精度损失", "部署优化模型"],
        "tools": ["PyTorch深度学习", "Docker容器"],
        "what_worked": ["蒸馏保留 95% 精度", "INT8 量化推理速度提升 3 倍", "显存占用减少 60%"],
        "what_failed": [],
        "why": "蒸馏配合量化在不显著损失精度的前提下大幅提升了推理效率",
    },
    {
        "domain": "数据处理",
        "task_type": "数据清洗",
        "intent": "设计数据质量保障体系：校验规则、异常检测和数据血缘追踪",
        "steps": ["定义数据质量维度", "实现校验规则引擎", "添加异常检测算法", "建立数据血缘图", "配置质量告警"],
        "tools": ["Elasticsearch搜索引擎", "Grafana监控"],
        "what_worked": ["规则引擎灵活可配", "异常检测发现隐藏问题", "血缘追踪定位根因"],
        "what_failed": [],
        "why": "系统化的数据质量体系从校验、检测到追踪形成闭环，保障数据可信",
    },
]


def generate_from_expert_templates(count: int) -> list[dict]:
    """生成专家级经验，置信度较高（0.7-0.9）."""
    experiences = []
    for i in range(count):
        template = random.choice(EXPERT_TEMPLATES)
        success = random.random() > 0.1  # 专家经验成功率更高
        days_ago = random.randint(0, 90)
        timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)

        steps = [
            {"action": s, "status": "completed" if success or j < len(template["steps"]) - 1 else "failed"}
            for j, s in enumerate(template["steps"])
        ]

        what_worked = template["what_worked"] if success else template["what_worked"][:1]
        what_failed = template["what_failed"] if not success else []
        why = template["why"] if success else f"专家方案执行中遇到挑战: {template['what_failed'][0] if template['what_failed'] else '环境差异'}"

        confidence = random.uniform(0.7, 0.9) if success else random.uniform(0.4, 0.6)

        experiences.append({
            "id": str(uuid.uuid4()),
            "timestamp": timestamp.isoformat(),
            "context": {
                "domain": template["domain"],
                "task_type": template["task_type"],
                "constraints": {
                    "env": random.choice(["生产环境", "预发布环境"]),
                    "timeout": random.choice([60, 120, 300]),
                    "resource_limit": "高",
                },
            },
            "intent": template["intent"],
            "execution": {
                "steps": steps,
                "tools": template["tools"],
                "trace": {
                    "duration_ms": random.randint(2000, 30000),
                    "commands_run": random.randint(6, 18),
                    "files_modified": random.randint(3, 10),
                },
            },
            "outcome": {
                "success": success,
                "metrics": {
                    "execution_time_s": random.uniform(2.0, 30.0),
                    "resource_usage_mb": random.randint(100, 1024),
                    "error_count": 0 if success else 1,
                },
            },
            "reflection": {
                "what_worked": what_worked,
                "what_failed": what_failed,
                "why": why,
            },
            "reusable_patterns": [
                {"pattern": f"专家最佳实践_{template['task_type']}", "applicable": True, "domain": template["domain"]},
                {"pattern": f"架构模式_{template['domain']}", "applicable": True, "domain": template["domain"]},
            ],
            "confidence_score": round(confidence, 4),
            "provenance": {
                "human_signals": [
                    {"contributor": "expert_architect", "contribution": "design"},
                    {"contributor": "senior_engineer", "contribution": "review"},
                ],
                "agent_signals": [
                    {"agent_id": f"agent-{random.randint(1, 10)}", "contribution": "execution"}
                ],
                "external_sources": [{"type": "expert_template", "name": template["task_type"]}],
            },
            "version": 1,
            "evaluation_status": "pending",
            "created_at": timestamp.isoformat(),
            "updated_at": timestamp.isoformat(),
        })
    return experiences


def generate_relations(experiences: list[dict], count: int = 2000) -> list[dict]:
    """Generate graph relations between experiences."""
    relations = []
    relation_types = ["reuse", "citation", "fork", "improvement", "dependency"]

    for _ in range(count):
        source = random.choice(experiences)
        target = random.choice(experiences)
        if source["id"] != target["id"]:
            relations.append({
                "id": str(uuid.uuid4()),
                "source_id": source["id"],
                "target_id": target["id"],
                "relation_type": random.choice(relation_types),
                "weight": round(random.uniform(0.3, 1.0), 2),
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    return relations


async def import_via_api(experiences: list[dict], api_url: str) -> int:
    """Import experiences via API."""
    import httpx

    imported = 0
    async with httpx.AsyncClient(timeout=30) as client:
        for i, exp in enumerate(experiences):
            try:
                # Remove fields not in Create schema
                create_data = {
                    "context": exp["context"],
                    "intent": exp["intent"],
                    "execution": exp["execution"],
                    "outcome": exp["outcome"],
                    "reflection": exp["reflection"],
                    "reusable_patterns": exp["reusable_patterns"],
                    "confidence_score": exp["confidence_score"],
                    "provenance": exp["provenance"],
                    "version": exp["version"],
                }
                response = await client.post(
                    f"{api_url}/api/v1/experiences",
                    json=create_data,
                )
                if response.status_code == 201:
                    imported += 1
                if (i + 1) % 100 == 0:
                    print(f"  Imported {i + 1}/{len(experiences)}...")
            except Exception as e:
                print(f"  Error importing experience {i}: {e}")

    return imported


async def import_via_db(experiences: list[dict], relations: list[dict]) -> int:
    """Import experiences directly to database."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))
    from app.core.database import async_session_factory, engine
    from app.models.experience import Experience, ExperienceRelation
    from sqlalchemy import text

    imported = 0
    async with async_session_factory() as session:
        # Enable pgvector
        await session.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        for i, exp_data in enumerate(experiences):
            exp = Experience(
                id=exp_data["id"],
                timestamp=datetime.fromisoformat(exp_data["timestamp"]),
                context=exp_data["context"],
                intent=exp_data["intent"],
                execution=exp_data["execution"],
                outcome=exp_data["outcome"],
                reflection=exp_data["reflection"],
                reusable_patterns=exp_data["reusable_patterns"],
                confidence_score=exp_data["confidence_score"],
                provenance=exp_data["provenance"],
                version=exp_data["version"],
                evaluation_status=exp_data["evaluation_status"],
                created_at=datetime.fromisoformat(exp_data["created_at"]),
                updated_at=datetime.fromisoformat(exp_data["updated_at"]),
            )
            session.add(exp)
            imported += 1

            if (i + 1) % 100 == 0:
                await session.commit()
                print(f"  Inserted {i + 1}/{len(experiences)}...")

        # Insert relations
        for rel_data in relations:
            rel = ExperienceRelation(
                id=rel_data["id"],
                source_id=rel_data["source_id"],
                target_id=rel_data["target_id"],
                relation_type=rel_data["relation_type"],
                weight=rel_data["weight"],
                created_at=datetime.fromisoformat(rel_data["created_at"]),
            )
            session.add(rel)

        await session.commit()

    await engine.dispose()
    return imported


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate seed experience data for Aevum OS")
    parser.add_argument("--count", type=int, default=10000, help="Number of experiences to generate")
    parser.add_argument("--output", type=str, help="Output JSON file path")
    parser.add_argument("--api", type=str, help="API URL for direct import")
    parser.add_argument("--db", action="store_true", help="Import directly to database")
    parser.add_argument("--relations", type=int, default=2000, help="Number of relations to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument(
        "--source",
        type=str,
        default="synthetic",
        choices=["synthetic", "datasets", "templates", "expert", "mixed"],
        help="Data source: synthetic (default), datasets, templates, expert, mixed",
    )

    args = parser.parse_args()
    random.seed(args.seed)

    # 根据数据源生成经验
    if args.source == "synthetic":
        print(f"Generating {args.count} synthetic seed experiences...")
        experiences = [generate_experience(i) for i in range(args.count)]
    elif args.source == "datasets":
        print(f"Generating {args.count} experiences from open datasets...")
        experiences = generate_from_open_datasets(args.count)
    elif args.source == "templates":
        print(f"Generating {args.count} experiences from workflow templates...")
        experiences = generate_from_workflow_templates(args.count)
    elif args.source == "expert":
        print(f"Generating {args.count} experiences from expert templates...")
        experiences = generate_from_expert_templates(args.count)
    elif args.source == "mixed":
        # 混合模式：各 25%
        per_source = args.count // 4
        remainder = args.count - per_source * 4
        print(f"Generating {args.count} mixed experiences (synthetic={per_source}, datasets={per_source}, templates={per_source}, expert={per_source + remainder})...")
        experiences = (
            [generate_experience(i) for i in range(per_source)]
            + generate_from_open_datasets(per_source)
            + generate_from_workflow_templates(per_source)
            + generate_from_expert_templates(per_source + remainder)
        )
        random.shuffle(experiences)
    else:
        experiences = []

    print(f"Generated {len(experiences)} experiences")

    print(f"Generating {args.relations} graph relations...")
    relations = generate_relations(experiences, args.relations)
    print(f"Generated {len(relations)} relations")

    # Domain distribution
    domain_counts: dict[str, int] = {}
    for exp in experiences:
        d = exp["context"]["domain"]
        domain_counts[d] = domain_counts.get(d, 0) + 1
    print("\nDomain distribution:")
    for d, c in sorted(domain_counts.items()):
        print(f"  {d}: {c} ({c/len(experiences)*100:.1f}%)")

    success_count = sum(1 for e in experiences if e["outcome"]["success"])
    print(f"\nSuccess rate: {success_count}/{len(experiences)} ({success_count/len(experiences)*100:.1f}%)")

    if args.output:
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"experiences": experiences, "relations": relations}, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to {output_path}")

    if args.api:
        print(f"\nImporting via API ({args.api})...")
        imported = asyncio.run(import_via_api(experiences, args.api))
        print(f"Imported {imported}/{len(experiences)} experiences")

    if args.db:
        print("\nImporting directly to database...")
        imported = asyncio.run(import_via_db(experiences, relations))
        print(f"Imported {imported} experiences and {len(relations)} relations")

    if not args.output and not args.api and not args.db:
        # Default: output to seeds.json
        output_path = Path("seeds.json")
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"experiences": experiences, "relations": relations}, f, ensure_ascii=False, indent=2)
        print(f"\nSaved to {output_path} (use --api or --db to import)")


if __name__ == "__main__":
    main()
