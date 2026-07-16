"""Unit tests for HumanExpression model and schemas."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.human_expression import HumanExpression
from app.schemas.human_expression import (
    HumanExpressionCreate,
    HumanExpressionUpdate,
    ObserveRequest,
)


class TestHumanExpressionModel:
    """Test HumanExpression ORM model."""

    def test_creation(self) -> None:
        user_id = uuid4()
        expr = HumanExpression(
            user_id=user_id,
            type="text",
            content={"text": "这是一个想法"},
            metadata_={"source": "web"},
        )
        assert expr.type == "text"
        assert expr.content == {"text": "这是一个想法"}
        assert expr.metadata_ == {"source": "web"}
        assert expr.user_id == user_id

    def test_repr(self) -> None:
        expr = HumanExpression(type="note", user_id=uuid4())
        repr_str = repr(expr)
        assert "HumanExpression" in repr_str
        assert "note" in repr_str

    def test_to_dict(self) -> None:
        user_id = uuid4()
        expr = HumanExpression(
            id=uuid4(),
            user_id=user_id,
            type="link",
            content={"url": "https://example.com"},
            metadata_={"title": "Example"},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        d = expr.to_dict()
        assert d["type"] == "link"
        assert d["content"] == {"url": "https://example.com"}
        assert d["metadata"] == {"title": "Example"}
        assert d["user_id"] == str(user_id)


class TestHumanExpressionSchemas:
    """Test Pydantic schemas."""

    def test_create_valid(self) -> None:
        data = HumanExpressionCreate(
            type="text",
            content={"text": "hello"},
        )
        assert data.type == "text"
        assert data.content == {"text": "hello"}
        assert data.metadata == {}

    def test_create_with_metadata(self) -> None:
        data = HumanExpressionCreate(
            type="note",
            content={"body": "idea"},
            metadata={"tags": ["dev", "ops"]},
        )
        assert data.metadata == {"tags": ["dev", "ops"]}

    def test_create_invalid_type(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            HumanExpressionCreate(type="invalid", content={})

    def test_update_partial(self) -> None:
        data = HumanExpressionUpdate(content={"new": "content"})
        assert data.content == {"new": "content"}
        assert data.metadata is None

    def test_observe_request(self) -> None:
        data = ObserveRequest(query="搜索表达")
        assert data.query == "搜索表达"
        assert data.limit == 5

    def test_observe_request_custom_limit(self) -> None:
        data = ObserveRequest(query="test", limit=20)
        assert data.limit == 20

    def test_observe_request_empty_query_rejected(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ObserveRequest(query="")

    def test_all_valid_types(self) -> None:
        for t in ["text", "image", "video", "audio", "link", "note"]:
            data = HumanExpressionCreate(type=t, content={})
            assert data.type == t
