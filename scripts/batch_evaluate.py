"""批量评估所有 pending 状态的经验."""

import asyncio
import sys

from sqlalchemy import select

from app.core.database import async_session_factory, engine
from app.models.experience import Experience
from app.models.evaluation import Evaluation
from app.services.evaluation.experience_evaluator import ExperienceEvaluator


async def batch_evaluate():
    evaluator = ExperienceEvaluator()
    evaluated = 0
    errors = 0

    async with async_session_factory() as session:
        result = await session.execute(
            select(Experience).where(Experience.evaluation_status == "pending")
        )
        experiences = result.scalars().all()
        total = len(experiences)
        print(f"Found {total} pending experiences to evaluate")

        for i, exp in enumerate(experiences):
            try:
                result = evaluator.evaluate(exp)

                exp.confidence_score = result.confidence_score
                exp.evaluation_status = "evaluated"

                eval_model = evaluator.to_evaluation_model(result)
                session.add(eval_model)

                evaluated += 1
                if (i + 1) % 100 == 0:
                    await session.commit()
                    print(f"  Evaluated {i + 1}/{total}...")
            except Exception as e:
                errors += 1
                print(f"  Error on {exp.id}: {e}")

        await session.commit()

    print(f"\nDone: {evaluated} evaluated, {errors} errors (total: {total})")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(batch_evaluate())
