"""Unit tests for WorldBridge model and schemas."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.world_bridge import WorldBridge
from app.schemas.world_bridge import BridgeCreate, BridgeResponse, BridgeListResponse


class TestWorldBridgeModel:
    """Test WorldBridge ORM model."""

    def test_creation(self) -> None:
        expr_id = uuid4()
        exp_id = uuid4()
        bridge = WorldBridge(
            bridge_type="inspiration",
            human_expression_id=expr_id,
            experience_id=exp_id,
            metadata_={"note": "user idea"},
            created_by="user-123",
        )
        assert bridge.bridge_type == "inspiration"
        assert bridge.human_expression_id == expr_id
        assert bridge.experience_id == exp_id
        assert bridge.metadata_ == {"note": "user idea"}
        assert bridge.created_by == "user-123"

    def test_repr(self) -> None:
        bridge = WorldBridge(
            bridge_type="observation",
            human_expression_id=uuid4(),
            experience_id=uuid4(),
            created_by="agent-1",
        )
        repr_str = repr(bridge)
        assert "WorldBridge" in repr_str
        assert "observation" in repr_str

    def test_to_dict(self) -> None:
        expr_id = uuid4()
        exp_id = uuid4()
        bridge = WorldBridge(
            id=uuid4(),
            bridge_type="reflection",
            human_expression_id=expr_id,
            experience_id=exp_id,
            metadata_={"rating": 5},
            created_by="user-1",
            created_at=datetime.now(timezone.utc),
        )
        d = bridge.to_dict()
        assert d["bridge_type"] == "reflection"
        assert d["human_expression_id"] == str(expr_id)
        assert d["experience_id"] == str(exp_id)
        assert d["metadata"] == {"rating": 5}
        assert d["created_by"] == "user-1"


class TestWorldBridgeSchemas:
    """Test Pydantic schemas."""

    def test_bridge_create_valid(self) -> None:
        expr_id = uuid4()
        exp_id = uuid4()
        data = BridgeCreate(
            bridge_type="inspiration",
            human_expression_id=expr_id,
            experience_id=exp_id,
        )
        assert data.bridge_type == "inspiration"
        assert data.human_expression_id == expr_id
        assert data.experience_id == exp_id
        assert data.metadata == {}

    def test_bridge_create_with_metadata(self) -> None:
        data = BridgeCreate(
            bridge_type="recommendation",
            human_expression_id=uuid4(),
            experience_id=uuid4(),
            metadata={"confidence": 0.9},
        )
        assert data.metadata == {"confidence": 0.9}

    def test_bridge_create_invalid_type(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            BridgeCreate(
                bridge_type="invalid",
                human_expression_id=uuid4(),
                experience_id=uuid4(),
            )

    def test_all_valid_bridge_types(self) -> None:
        for bt in ["inspiration", "observation", "recommendation", "reflection"]:
            data = BridgeCreate(
                bridge_type=bt,
                human_expression_id=uuid4(),
                experience_id=uuid4(),
            )
            assert data.bridge_type == bt

    def test_bridge_response(self) -> None:
        now = datetime.now(timezone.utc)
        resp = BridgeResponse(
            id=uuid4(),
            bridge_type="reflection",
            human_expression_id=uuid4(),
            experience_id=uuid4(),
            metadata={"comment": "good"},
            created_by="user-1",
            created_at=now,
        )
        assert resp.bridge_type == "reflection"
        assert resp.metadata == {"comment": "good"}

    def test_bridge_list_response(self) -> None:
        resp = BridgeListResponse(items=[], total=0)
        assert resp.items == []
        assert resp.total == 0
