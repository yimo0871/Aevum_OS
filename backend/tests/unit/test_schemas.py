"""Unit tests for Pydantic schemas (API contracts)."""

import pytest
from pydantic import ValidationError


class TestExperienceContext:
    """Test ExperienceContext schema."""

    def test_valid_context(self) -> None:
        from app.schemas.experience import ExperienceContext

        ctx = ExperienceContext(domain="devops", task_type="deployment", constraints={"env": "prod"})
        assert ctx.domain == "devops"
        assert ctx.task_type == "deployment"
        assert ctx.constraints == {"env": "prod"}

    def test_default_constraints(self) -> None:
        from app.schemas.experience import ExperienceContext

        ctx = ExperienceContext(domain="frontend", task_type="testing")
        assert ctx.constraints == {}


class TestExperienceCreate:
    """Test ExperienceCreate schema."""

    def test_valid_create(self, sample_experience_data: dict) -> None:
        from app.schemas.experience import ExperienceCreate

        exp = ExperienceCreate(**sample_experience_data)
        assert exp.intent == sample_experience_data["intent"]
        assert exp.confidence_score == 0.92
        assert exp.version == 1

    def test_empty_intent_rejected(self) -> None:
        from app.schemas.experience import ExperienceCreate

        with pytest.raises(ValidationError, match="intent must not be empty"):
            ExperienceCreate(
                context={"domain": "test", "task_type": "test", "constraints": {}},
                intent="   ",
                outcome={"success": True, "metrics": {}},
            )

    def test_confidence_score_bounds(self) -> None:
        from app.schemas.experience import ExperienceCreate

        with pytest.raises(ValidationError):
            ExperienceCreate(
                context={"domain": "test", "task_type": "test", "constraints": {}},
                intent="test",
                outcome={"success": True, "metrics": {}},
                confidence_score=1.5,
            )

        with pytest.raises(ValidationError):
            ExperienceCreate(
                context={"domain": "test", "task_type": "test", "constraints": {}},
                intent="test",
                outcome={"success": True, "metrics": {}},
                confidence_score=-0.1,
            )

    def test_version_must_be_positive(self) -> None:
        from app.schemas.experience import ExperienceCreate

        with pytest.raises(ValidationError):
            ExperienceCreate(
                context={"domain": "test", "task_type": "test", "constraints": {}},
                intent="test",
                outcome={"success": True, "metrics": {}},
                version=0,
            )


class TestExperienceUpdate:
    """Test ExperienceUpdate schema."""

    def test_partial_update(self) -> None:
        from app.schemas.experience import ExperienceUpdate

        update = ExperienceUpdate(confidence_score=0.95)
        assert update.confidence_score == 0.95
        assert update.intent is None

    def test_empty_update(self) -> None:
        from app.schemas.experience import ExperienceUpdate

        update = ExperienceUpdate()
        assert update.confidence_score is None
        assert update.intent is None


class TestRelationCreate:
    """Test RelationCreate schema."""

    def test_valid_relation(self) -> None:
        from uuid import uuid4

        from app.schemas.experience import RelationCreate

        rel = RelationCreate(
            target_id=uuid4(),
            relation_type="reuse",
            weight=0.8,
        )
        assert rel.relation_type == "reuse"
        assert rel.weight == 0.8

    def test_invalid_relation_type(self) -> None:
        from uuid import uuid4

        from app.schemas.experience import RelationCreate

        with pytest.raises(ValidationError):
            RelationCreate(
                target_id=uuid4(),
                relation_type="invalid_type",
            )

    @pytest.mark.parametrize("rel_type", ["reuse", "citation", "fork", "improvement", "dependency"])
    def test_all_valid_relation_types(self, rel_type: str) -> None:
        from uuid import uuid4

        from app.schemas.experience import RelationCreate

        rel = RelationCreate(target_id=uuid4(), relation_type=rel_type)
        assert rel.relation_type == rel_type


class TestExperienceSearchRequest:
    """Test ExperienceSearchRequest schema."""

    def test_valid_search(self) -> None:
        from app.schemas.experience import ExperienceSearchRequest

        req = ExperienceSearchRequest(query="deploy fastapi", domain="devops", limit=5)
        assert req.query == "deploy fastapi"
        assert req.domain == "devops"
        assert req.limit == 5

    def test_empty_query_rejected(self) -> None:
        from app.schemas.experience import ExperienceSearchRequest

        with pytest.raises(ValidationError):
            ExperienceSearchRequest(query="")

    def test_limit_bounds(self) -> None:
        from app.schemas.experience import ExperienceSearchRequest

        with pytest.raises(ValidationError):
            ExperienceSearchRequest(query="test", limit=0)

        with pytest.raises(ValidationError):
            ExperienceSearchRequest(query="test", limit=101)
