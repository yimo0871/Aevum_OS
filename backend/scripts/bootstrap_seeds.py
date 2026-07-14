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

DOMAINS = ["devops", "frontend", "backend", "data", "testing", "security", "ml", "general"]

TASK_TYPES = {
    "devops": ["deployment", "ci_cd", "infrastructure", "monitoring", "containerization"],
    "frontend": ["ui_component", "page_layout", "state_management", "performance", "accessibility"],
    "backend": ["api_design", "database_migration", "authentication", "caching", "error_handling"],
    "data": ["etl_pipeline", "data_cleaning", "analysis", "visualization", "model_training"],
    "testing": ["unit_test", "integration_test", "e2e_test", "load_test", "security_test"],
    "security": ["vulnerability_scan", "auth_audit", "encryption", "penetration_test", "compliance"],
    "ml": ["model_training", "feature_engineering", "evaluation", "deployment", "optimization"],
    "general": ["documentation", "refactoring", "code_review", "planning", "research"],
}

INTENTS = {
    "deployment": [
        "Deploy {app} to {env} environment using {tool}",
        "Set up {tool} pipeline for {app} deployment to {env}",
        "Configure {tool} for zero-downtime deployment of {app}",
    ],
    "ci_cd": [
        "Create CI/CD pipeline for {app} with {tool}",
        "Automate testing and deployment for {app} using {tool}",
        "Set up {tool} workflow for {app} continuous integration",
    ],
    "unit_test": [
        "Write unit tests for {app} module using {tool}",
        "Achieve {coverage}% test coverage for {app} with {tool}",
        "Set up {tool} testing framework for {app}",
    ],
    "api_design": [
        "Design RESTful API for {app} with {tool}",
        "Implement {tool} endpoints for {app} CRUD operations",
        "Create GraphQL schema for {app} using {tool}",
    ],
    "model_training": [
        "Train {model} model on {dataset} using {tool}",
        "Fine-tune {model} for {task} with {tool}",
        "Evaluate {model} performance on {dataset} with {tool}",
    ],
}

TOOLS = ["docker", "kubernetes", "git", "pytest", "jest", "nginx", "redis", "postgresql",
         "mongodb", "elasticsearch", "grafana", "prometheus", "terraform", "ansible",
         "jenkins", "github_actions", "react", "vue", "fastapi", "django", "flask",
         "langchain", "openai", "pandas", "numpy", "scikit-learn", "pytorch", "tensorflow"]

APPS = ["user-service", "auth-service", "payment-api", "dashboard", "mobile-app",
        "data-pipeline", "ml-model", "notification-service", "search-engine", "analytics"]

ENVS = ["production", "staging", "development", "testing"]
MODELS = ["BERT", "GPT", "ResNet", "YOLO", "LLaMA", "Transformer"]
DATASETS = ["MNIST", "CIFAR-10", "ImageNet", "COCO", "Wikipedia", "Common Crawl"]
TASKS = ["classification", "detection", "generation", "summarization", "translation"]
COVERAGE = ["80", "85", "90", "95", "100"]


def generate_intent(domain: str, task_type: str) -> str:
    """Generate a realistic intent string."""
    templates = INTENTS.get(task_type, [
        f"Execute {task_type} task for {domain} application",
        f"Perform {task_type} in {domain} context",
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
            "Standard pattern applied", "Tool configuration correct", "Environment setup verified",
            "Pre-checks passed", "Rollback plan ready", "Monitoring enabled",
        ], random.randint(1, 3))
    else:
        what_failed = random.sample([
            "Port conflict", "Permission denied", "Timeout exceeded", "Dependency missing",
            "Configuration error", "Network unreachable", "Resource limit exceeded",
        ], random.randint(1, 2))
        what_worked = random.sample([
            "Initial setup completed", "Partial execution before failure",
        ], random.randint(0, 1))

    confidence = random.uniform(0.3, 0.95) if success else random.uniform(0.1, 0.5)

    patterns_count = random.randint(0, 3)
    reusable_patterns = [
        {"pattern": f"pattern_{i}", "applicable": True, "domain": domain}
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
                "resource_limit": random.choice(["low", "medium", "high"]),
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
            "why": "Standard execution pattern" if success else "Unexpected configuration issue",
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

    args = parser.parse_args()
    random.seed(args.seed)

    print(f"Generating {args.count} seed experiences...")
    experiences = [generate_experience(i) for i in range(args.count)]
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
