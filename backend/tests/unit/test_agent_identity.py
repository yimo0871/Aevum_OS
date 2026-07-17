"""Unit tests for IdentityManager and Agent DID - 身份与所有权管理."""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.models.agent import Agent
from app.models.experience import Experience
from app.services.governance.identity import IdentityManager


# ── Helpers ──


def _make_agent(**overrides) -> Agent:
    """Build an Agent ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        name="Test Agent",
        description="A test agent",
        api_key="test-api-key-123",
        is_active=True,
        capabilities={},
        did=None,
        owner_name=None,
    )
    defaults.update(overrides)
    return Agent(**defaults)


def _make_experience(**overrides) -> Experience:
    """Build an Experience ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        context={"domain": "devops"},
        intent="Deploy application",
        execution={},
        outcome={"success": True},
        reflection={},
        reusable_patterns=[],
        confidence_score=0.8,
        provenance={},
        version=1,
        status="active",
        compressed=False,
        owner_agent_id=None,
    )
    defaults.update(overrides)
    return Experience(**defaults)


# ── Agent model DID field tests ──


class TestAgentDIDField:
    """Test Agent model DID/owner_name fields."""

    def test_agent_has_did_field(self) -> None:
        agent = _make_agent(did="did:aevum:123")
        assert agent.did == "did:aevum:123"

    def test_agent_has_owner_name_field(self) -> None:
        agent = _make_agent(owner_name="Alice")
        assert agent.owner_name == "Alice"

    def test_agent_did_default_none(self) -> None:
        agent = _make_agent()
        assert agent.did is None

    def test_agent_repr(self) -> None:
        agent = _make_agent(name="MyAgent")
        assert "MyAgent" in repr(agent)


# ── generate_did tests ──


class TestGenerateDID:
    """Test IdentityManager.generate_did."""

    @pytest.mark.asyncio
    async def test_generate_did_creates_did(self) -> None:
        agent = _make_agent()
        session = AsyncMock()
        session.get = AsyncMock(return_value=agent)
        session.flush = AsyncMock()

        manager = IdentityManager()
        did = await manager.generate_did(agent.id, session)

        assert did.startswith("did:aevum:")
        assert agent.did == did

    @pytest.mark.asyncio
    async def test_generate_did_idempotent(self) -> None:
        existing_did = "did:aevum:existing-123"
        agent = _make_agent(did=existing_did)
        session = AsyncMock()
        session.get = AsyncMock(return_value=agent)

        manager = IdentityManager()
        did = await manager.generate_did(agent.id, session)

        assert did == existing_did
        session.flush.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_generate_did_agent_not_found_raises(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        manager = IdentityManager()
        with pytest.raises(ValueError, match="Agent 不存在"):
            await manager.generate_did(uuid.uuid4(), session)

    @pytest.mark.asyncio
    async def test_generate_did_format(self) -> None:
        agent = _make_agent()
        session = AsyncMock()
        session.get = AsyncMock(return_value=agent)
        session.flush = AsyncMock()

        manager = IdentityManager()
        did = await manager.generate_did(agent.id, session)

        parts = did.split(":")
        assert parts[0] == "did"
        assert parts[1] == "aevum"
        assert len(parts) == 3
        # The UUID part should be parseable
        uuid.UUID(parts[2])


# ── assign_ownership tests ──


class TestAssignOwnership:
    """Test IdentityManager.assign_ownership."""

    @pytest.mark.asyncio
    async def test_assign_ownership_sets_owner(self) -> None:
        agent = _make_agent()
        exp = _make_experience()
        session = AsyncMock()
        session.get = AsyncMock(side_effect=[agent, exp])
        session.flush = AsyncMock()

        manager = IdentityManager()
        result = await manager.assign_ownership(exp.id, agent.id, session)

        assert result is exp
        assert exp.owner_agent_id == agent.id

    @pytest.mark.asyncio
    async def test_assign_ownership_agent_not_found_raises(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        manager = IdentityManager()
        with pytest.raises(ValueError, match="Agent 不存在"):
            await manager.assign_ownership(uuid.uuid4(), uuid.uuid4(), session)

    @pytest.mark.asyncio
    async def test_assign_ownership_experience_not_found_returns_none(self) -> None:
        agent = _make_agent()
        session = AsyncMock()
        session.get = AsyncMock(side_effect=[agent, None])

        manager = IdentityManager()
        result = await manager.assign_ownership(uuid.uuid4(), agent.id, session)

        assert result is None

    @pytest.mark.asyncio
    async def test_assign_ownership_overwrites_previous(self) -> None:
        old_agent_id = uuid.uuid4()
        new_agent = _make_agent()
        exp = _make_experience(owner_agent_id=old_agent_id)
        session = AsyncMock()
        session.get = AsyncMock(side_effect=[new_agent, exp])
        session.flush = AsyncMock()

        manager = IdentityManager()
        await manager.assign_ownership(exp.id, new_agent.id, session)

        assert exp.owner_agent_id == new_agent.id


# ── get_owner tests ──


class TestGetOwner:
    """Test IdentityManager.get_owner."""

    @pytest.mark.asyncio
    async def test_get_owner_returns_agent(self) -> None:
        agent = _make_agent()
        exp = _make_experience(owner_agent_id=agent.id)
        session = AsyncMock()
        session.get = AsyncMock(side_effect=[exp, agent])

        manager = IdentityManager()
        result = await manager.get_owner(exp.id, session)

        assert result is agent

    @pytest.mark.asyncio
    async def test_get_owner_no_owner_returns_none(self) -> None:
        exp = _make_experience(owner_agent_id=None)
        session = AsyncMock()
        session.get = AsyncMock(return_value=exp)

        manager = IdentityManager()
        result = await manager.get_owner(exp.id, session)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_owner_experience_not_found_returns_none(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        manager = IdentityManager()
        result = await manager.get_owner(uuid.uuid4(), session)

        assert result is None


# ── verify_ownership tests ──


class TestVerifyOwnership:
    """Test IdentityManager.verify_ownership."""

    @pytest.mark.asyncio
    async def test_verify_ownership_true(self) -> None:
        agent_id = uuid.uuid4()
        exp = _make_experience(owner_agent_id=agent_id)
        session = AsyncMock()
        session.get = AsyncMock(return_value=exp)

        manager = IdentityManager()
        result = await manager.verify_ownership(exp.id, agent_id, session)

        assert result is True

    @pytest.mark.asyncio
    async def test_verify_ownership_false_different_agent(self) -> None:
        agent_id = uuid.uuid4()
        other_agent_id = uuid.uuid4()
        exp = _make_experience(owner_agent_id=agent_id)
        session = AsyncMock()
        session.get = AsyncMock(return_value=exp)

        manager = IdentityManager()
        result = await manager.verify_ownership(exp.id, other_agent_id, session)

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_ownership_false_no_owner(self) -> None:
        exp = _make_experience(owner_agent_id=None)
        session = AsyncMock()
        session.get = AsyncMock(return_value=exp)

        manager = IdentityManager()
        result = await manager.verify_ownership(exp.id, uuid.uuid4(), session)

        assert result is False

    @pytest.mark.asyncio
    async def test_verify_ownership_false_experience_not_found(self) -> None:
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        manager = IdentityManager()
        result = await manager.verify_ownership(uuid.uuid4(), uuid.uuid4(), session)

        assert result is False


# ── Experience owner_agent_id field test ──


class TestExperienceOwnerField:
    """Test Experience model owner_agent_id field."""

    def test_experience_has_owner_agent_id(self) -> None:
        agent_id = uuid.uuid4()
        exp = _make_experience(owner_agent_id=agent_id)
        assert exp.owner_agent_id == agent_id

    def test_experience_owner_agent_id_default_none(self) -> None:
        exp = _make_experience()
        assert exp.owner_agent_id is None
