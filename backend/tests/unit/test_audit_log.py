"""Unit tests for AuditLogger and AuditLog model - 审计日志系统."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.audit_log import AuditLog
from app.services.governance.audit import AuditLogger


# ── Helpers ──


def _make_audit_log(**overrides) -> AuditLog:
    """Build an AuditLog ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        action="create",
        entity_type="experience",
        entity_id=uuid.uuid4(),
        actor_id=uuid.uuid4(),
        actor_type="user",
        details={"note": "test"},
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return AuditLog(**defaults)


# ── AuditLog model tests ──


class TestAuditLogModel:
    """Test AuditLog ORM model."""

    def test_creation(self) -> None:
        log = _make_audit_log(action="compress", entity_type="experience")
        assert log.action == "compress"
        assert log.entity_type == "experience"

    def test_repr(self) -> None:
        log = _make_audit_log(action="forget")
        repr_str = repr(log)
        assert "AuditLog" in repr_str
        assert "forget" in repr_str

    def test_to_dict(self) -> None:
        log = _make_audit_log()
        d = log.to_dict()
        assert d["action"] == "create"
        assert d["entity_type"] == "experience"
        assert d["actor_type"] == "user"
        assert d["id"] == str(log.id)
        assert d["entity_id"] == str(log.entity_id)
        assert d["actor_id"] == str(log.actor_id)
        assert "created_at" in d

    def test_to_dict_null_actor(self) -> None:
        log = _make_audit_log(actor_id=None, actor_type="system")
        d = log.to_dict()
        assert d["actor_id"] is None
        assert d["actor_type"] == "system"


# ── AuditLogger.log tests ──


class TestAuditLoggerLog:
    """Test AuditLogger.log."""

    @pytest.mark.asyncio
    async def test_log_creates_entry(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        logger = AuditLogger()
        entity_id = uuid.uuid4()
        actor_id = uuid.uuid4()

        result = await logger.log(
            action="compress",
            entity_type="experience",
            entity_id=entity_id,
            session=session,
            actor_id=actor_id,
            actor_type="user",
            details={"reason": "test"},
        )

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        assert result.action == "compress"
        assert result.entity_type == "experience"
        assert result.entity_id == entity_id
        assert result.actor_id == actor_id

    @pytest.mark.asyncio
    async def test_log_system_actor_no_actor_id(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        logger = AuditLogger()
        result = await logger.log(
            action="forget",
            entity_type="experience",
            entity_id=uuid.uuid4(),
            session=session,
            actor_type="system",
        )

        assert result.actor_id is None
        assert result.actor_type == "system"
        assert result.details == {}

    @pytest.mark.asyncio
    async def test_log_invalid_action_raises(self) -> None:
        session = AsyncMock()
        logger = AuditLogger()

        with pytest.raises(ValueError, match="无效的操作类型"):
            await logger.log(
                action="invalid",
                entity_type="experience",
                entity_id=uuid.uuid4(),
                session=session,
            )

    @pytest.mark.asyncio
    async def test_log_invalid_entity_type_raises(self) -> None:
        session = AsyncMock()
        logger = AuditLogger()

        with pytest.raises(ValueError, match="无效的实体类型"):
            await logger.log(
                action="create",
                entity_type="invalid",
                entity_id=uuid.uuid4(),
                session=session,
            )

    @pytest.mark.asyncio
    async def test_log_invalid_actor_type_raises(self) -> None:
        session = AsyncMock()
        logger = AuditLogger()

        with pytest.raises(ValueError, match="无效的操作者类型"):
            await logger.log(
                action="create",
                entity_type="experience",
                entity_id=uuid.uuid4(),
                session=session,
                actor_type="invalid",
            )

    @pytest.mark.asyncio
    async def test_log_all_valid_actions(self) -> None:
        session = AsyncMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        logger = AuditLogger()
        for action in ["create", "update", "delete", "access", "fork", "cite", "compress", "forget"]:
            session.reset_mock()
            result = await logger.log(
                action=action,
                entity_type="experience",
                entity_id=uuid.uuid4(),
                session=session,
            )
            assert result.action == action


# ── AuditLogger.get_logs tests ──


class TestAuditLoggerGetLogs:
    """Test AuditLogger.get_logs."""

    @pytest.mark.asyncio
    async def test_get_logs_returns_entity_trail(self) -> None:
        entity_id = uuid.uuid4()
        logs = [
            _make_audit_log(entity_id=entity_id, action="create"),
            _make_audit_log(entity_id=entity_id, action="update"),
        ]
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = logs
        session.execute = AsyncMock(return_value=result_mock)

        logger = AuditLogger()
        result = await logger.get_logs("experience", entity_id, session)

        assert len(result) == 2
        assert result == logs
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_logs_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        logger = AuditLogger()
        result = await logger.get_logs("experience", uuid.uuid4(), session)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_logs_with_limit(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        logger = AuditLogger()
        await logger.get_logs("experience", uuid.uuid4(), session, limit=10)

        session.execute.assert_awaited_once()


# ── AuditLogger.get_actor_logs tests ──


class TestAuditLoggerGetActorLogs:
    """Test AuditLogger.get_actor_logs."""

    @pytest.mark.asyncio
    async def test_get_actor_logs_returns_history(self) -> None:
        actor_id = uuid.uuid4()
        logs = [
            _make_audit_log(actor_id=actor_id, action="create"),
            _make_audit_log(actor_id=actor_id, action="delete"),
        ]
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = logs
        session.execute = AsyncMock(return_value=result_mock)

        logger = AuditLogger()
        result = await logger.get_actor_logs(actor_id, session)

        assert len(result) == 2
        assert all(log.actor_id == actor_id for log in result)

    @pytest.mark.asyncio
    async def test_get_actor_logs_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        logger = AuditLogger()
        result = await logger.get_actor_logs(uuid.uuid4(), session)

        assert result == []


# ── AuditLogger.get_logs_by_action tests ──


class TestAuditLoggerGetLogsByAction:
    """Test AuditLogger.get_logs_by_action."""

    @pytest.mark.asyncio
    async def test_get_logs_by_action(self) -> None:
        logs = [_make_audit_log(action="compress"), _make_audit_log(action="compress")]
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = logs
        session.execute = AsyncMock(return_value=result_mock)

        logger = AuditLogger()
        result = await logger.get_logs_by_action("compress", session)

        assert len(result) == 2
        assert all(log.action == "compress" for log in result)
