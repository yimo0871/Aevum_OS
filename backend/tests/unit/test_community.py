"""Unit tests for Community model and schemas."""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.models.community import Community, user_community
from app.schemas.community import (
    CommunityCreate,
    CommunityResponse,
    CommunityUpdate,
    CommunityMemberResponse,
)


class TestCommunityModel:
    """Test Community ORM model."""

    def test_community_creation(self) -> None:
        owner_id = uuid4()
        community = Community(
            name="DevOps 社区",
            description="DevOps 最佳经验共享",
            owner_id=owner_id,
            visibility="open",
        )
        assert community.name == "DevOps 社区"
        assert community.description == "DevOps 最佳经验共享"
        assert community.owner_id == owner_id
        assert community.visibility == "open"

    def test_community_defaults(self) -> None:
        owner_id = uuid4()
        community = Community(name="Test", owner_id=owner_id)
        # visibility defaults to "open" at DB level (server_default)
        # Before flush, Python-side default may not be set yet
        assert community.name == "Test"
        assert community.owner_id == owner_id

    def test_community_repr(self) -> None:
        community = Community(name="Test Community", owner_id=uuid4())
        repr_str = repr(community)
        assert "Community" in repr_str
        assert "Test Community" in repr_str


class TestCommunitySchemas:
    """Test Community Pydantic schemas."""

    def test_community_create_valid(self) -> None:
        data = CommunityCreate(name="DevOps 社区", description="共享经验")
        assert data.name == "DevOps 社区"
        assert data.visibility == "open"

    def test_community_create_invite(self) -> None:
        data = CommunityCreate(name="Private", visibility="invite")
        assert data.visibility == "invite"

    def test_community_create_invalid_visibility(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CommunityCreate(name="Test", visibility="invalid")

    def test_community_create_short_name(self) -> None:
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CommunityCreate(name="a")

    def test_community_update_partial(self) -> None:
        data = CommunityUpdate(description="New description")
        assert data.description == "New description"
        assert data.name is None

    def test_community_response_from_attributes(self) -> None:
        owner_id = uuid4()
        community = Community(
            id=uuid4(),
            name="Test",
            description="Desc",
            owner_id=owner_id,
            visibility="open",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        response = CommunityResponse(
            id=community.id,
            name=community.name,
            description=community.description,
            owner_id=community.owner_id,
            visibility=community.visibility,
            member_count=1,
            created_at=community.created_at,
            updated_at=community.updated_at,
        )
        assert response.name == "Test"
        assert response.member_count == 1

    def test_community_member_response(self) -> None:
        user_id = uuid4()
        member = CommunityMemberResponse(
            user_id=user_id,
            username="testuser",
            email="test@test.com",
            role="admin",
            joined_at=datetime.now(timezone.utc),
        )
        assert member.role == "admin"
        assert member.username == "testuser"
