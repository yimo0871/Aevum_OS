"""agents API 路由单元测试.

覆盖端点:
- POST   /agents                 (创建Agent / 返回api_key)
- GET    /agents                 (列出Agent / 空列表)
- DELETE /agents/{id}            (删除成功 / 不存在404)
- POST   /agents/{id}/regenerate-key  (重生成key / 不存在404)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.agents import create_agent, list_agents, delete_agent, regenerate_key
from app.schemas.agent import AgentCreate


def _make_agent(
    aid=None,
    user_id=None,
    name="TestAgent",
    api_key="sk-test-key-123",
    is_active=True,
):
    """创建模拟 Agent 对象."""
    agent = MagicMock()
    agent.id = aid or uuid4()
    agent.user_id = user_id or uuid4()
    agent.name = name
    agent.description = "Test description"
    agent.api_key = api_key
    agent.is_active = is_active
    agent.capabilities = {"code": True}
    agent.created_at = datetime.now(timezone.utc)
    agent.last_active_at = None
    return agent


def _make_user(uid=None):
    """创建模拟 User 对象."""
    user = MagicMock()
    user.id = uid or uuid4()
    return user


def _mock_session(scalar_result=None, scalars_result=None):
    """创建模拟 AsyncSession."""
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = scalar_result
    if scalars_result is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = scalars_result
        result.scalars.return_value = scalars_mock
    session.execute.return_value = result
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    return session


# ── create_agent 测试 ──


class TestCreateAgent:
    @pytest.mark.asyncio
    async def test_create_agent_success(self):
        """创建 Agent 成功 -> 返回含 api_key."""
        uid = uuid4()
        user = _make_user(uid)
        session = _mock_session()

        async def _flush_side_effect(*args, **kwargs):
            added = session.add.call_args[0][0]
            added.id = uuid4()
            added.created_at = datetime.now(timezone.utc)
            added.is_active = True

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        data = AgentCreate(name="MyAgent", description="A test agent")

        result = await create_agent(data, user, session)

        assert result.name == "MyAgent"
        assert result.api_key  # api_key 不为空
        assert len(result.api_key) > 10  # 足够长
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_agent_associated_with_user(self):
        """Agent 的 user_id 应为当前用户."""
        uid = uuid4()
        user = _make_user(uid)
        session = _mock_session()

        async def _flush_side_effect(*args, **kwargs):
            added = session.add.call_args[0][0]
            added.id = uuid4()
            added.created_at = datetime.now(timezone.utc)
            added.is_active = True

        session.flush = AsyncMock(side_effect=_flush_side_effect)
        data = AgentCreate(name="MyAgent")

        result = await create_agent(data, user, session)

        # 验证 session.add 收到的对象有正确的 user_id
        added_agent = session.add.call_args[0][0]
        assert added_agent.user_id == uid


# ── list_agents 测试 ──


class TestListAgents:
    @pytest.mark.asyncio
    async def test_list_agents_with_data(self):
        """列出用户的 Agent -> 返回列表."""
        uid = uuid4()
        user = _make_user(uid)
        agents = [
            _make_agent(name="Agent1", user_id=uid),
            _make_agent(name="Agent2", user_id=uid),
        ]
        session = _mock_session(scalars_result=agents)

        result = await list_agents(user, session)

        assert len(result) == 2
        assert result[0].name == "Agent1"
        assert result[1].name == "Agent2"

    @pytest.mark.asyncio
    async def test_list_agents_empty(self):
        """用户没有 Agent -> 返回空列表."""
        user = _make_user()
        session = _mock_session(scalars_result=[])

        result = await list_agents(user, session)

        assert len(result) == 0


# ── delete_agent 测试 ──


class TestDeleteAgent:
    @pytest.mark.asyncio
    async def test_delete_agent_success(self):
        """删除自己的 Agent 成功."""
        uid = uuid4()
        user = _make_user(uid)
        agent = _make_agent(user_id=uid)
        session = _mock_session(scalar_result=agent)

        await delete_agent(agent.id, user, session)

        session.delete.assert_awaited_once_with(agent)

    @pytest.mark.asyncio
    async def test_delete_nonexistent_agent_returns_404(self):
        """Agent 不存在 -> 404."""
        user = _make_user()
        session = _mock_session(scalar_result=None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_agent(uuid4(), user, session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_other_users_agent_returns_404(self):
        """删除他人的 Agent -> 404 (查询条件含 user_id 过滤)."""
        uid = uuid4()
        user = _make_user(uid)
        other_uid = uuid4()
        # 查询条件 WHERE agent_id=? AND user_id=current_user
        # 不会返回他人的 Agent
        session = _mock_session(scalar_result=None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_agent(uuid4(), user, session)
        assert exc_info.value.status_code == 404


# ── regenerate_key 测试 ──


class TestRegenerateKey:
    @pytest.mark.asyncio
    async def test_regenerate_key_success(self):
        """重新生成 API Key 成功."""
        uid = uuid4()
        user = _make_user(uid)
        old_key = "sk-old-key-123"
        agent = _make_agent(user_id=uid, api_key=old_key)
        session = _mock_session(scalar_result=agent)

        result = await regenerate_key(agent.id, user, session)

        assert result.api_key != old_key  # key 已变更
        assert len(result.api_key) > 10
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_regenerate_key_nonexistent_returns_404(self):
        """Agent 不存在 -> 404."""
        user = _make_user()
        session = _mock_session(scalar_result=None)

        with pytest.raises(HTTPException) as exc_info:
            await regenerate_key(uuid4(), user, session)
        assert exc_info.value.status_code == 404
