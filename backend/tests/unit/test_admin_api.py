"""admin API 路由单元测试.

覆盖端点:
- GET    /admin/users              (分页列出用户)
- GET    /admin/users/{id}         (用户详情 / 不存在404)
- PUT    /admin/users/{id}         (激活/禁用/设管理员 / 不存在404)
- DELETE /admin/users/{id}         (删除 / 不存在404 / 不能删自己400)
- GET    /admin/experiences        (列出所有经验)
- DELETE /admin/experiences/{id}   (删除经验 / 不存在404)
- PUT    /admin/experiences/{id}/status  (更新状态 / 不存在404)
- GET    /admin/agents             (列出所有Agent)
- GET    /admin/stats              (系统统计)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.admin import (
    UserUpdateRequest,
    ExperienceStatusUpdate,
    list_users,
    get_user,
    update_user,
    delete_user,
    list_experiences,
    delete_experience,
    update_experience_status,
    list_agents,
    system_stats,
)


# ── 工具函数 ──


def _make_user(
    uid=None,
    email="admin@example.com",
    username="admin",
    is_active=True,
    is_admin=True,
    bio="",
):
    user = MagicMock()
    user.id = uid or uuid4()
    user.email = email
    user.username = username
    user.is_active = is_active
    user.is_admin = is_admin
    user.bio = bio
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _make_experience(eid=None, user_id=None, status="pending"):
    exp = MagicMock()
    exp.id = eid or uuid4()
    exp.user_id = user_id
    exp.evaluation_status = status
    exp.created_at = datetime.now(timezone.utc)
    exp.to_dict.return_value = {"id": str(exp.id), "evaluation_status": status}
    return exp


def _make_agent(aid=None, user_id=None, name="TestAgent"):
    agent = MagicMock()
    agent.id = aid or uuid4()
    agent.user_id = user_id or uuid4()
    agent.name = name
    agent.api_key = "sk-test-key-1234567890"
    agent.is_active = True
    agent.created_at = datetime.now(timezone.utc)
    agent.last_active_at = None
    return agent


def _mock_session(scalar_result=None, scalars_result=None, get_result=None, all_rows=None):
    """创建模拟 AsyncSession."""
    session = AsyncMock()
    result = MagicMock()
    if scalar_result is not None:
        result.scalar_one_or_none.return_value = scalar_result
        result.scalar.return_value = scalar_result
    if scalars_result is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = scalars_result
        result.scalars.return_value = scalars_mock
    if all_rows is not None:
        result.all.return_value = all_rows
    session.execute.return_value = result
    session.flush = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    if get_result is not None:
        session.get = AsyncMock(return_value=get_result)
    else:
        session.get = AsyncMock(return_value=None)
    return session


# ── list_users 测试 ──


class TestListUsers:
    @pytest.mark.asyncio
    async def test_list_users_success(self):
        """管理员列出用户 -> 分页结果."""
        admin = _make_user()
        users = [_make_user(username="u1"), _make_user(username="u2")]
        session = _mock_session(scalars_result=users, scalar_result=2)

        result = await list_users(page=1, page_size=20, admin=admin, session=session)

        assert result["total"] == 2
        assert len(result["items"]) == 2
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_list_users_empty(self):
        """无用户 -> 空列表."""
        admin = _make_user()
        session = _mock_session(scalars_result=[], scalar_result=0)

        result = await list_users(page=1, page_size=20, admin=admin, session=session)

        assert result["total"] == 0
        assert len(result["items"]) == 0


# ── get_user 测试 ──


class TestGetUser:
    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """获取用户详情成功."""
        admin = _make_user()
        target = _make_user(username="target")
        session = _mock_session(get_result=target)

        result = await get_user(target.id, admin, session)

        assert result["username"] == "target"

    @pytest.mark.asyncio
    async def test_get_user_not_found_returns_404(self):
        """用户不存在 -> 404."""
        admin = _make_user()
        session = _mock_session(get_result=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_user(uuid4(), admin, session)
        assert exc_info.value.status_code == 404


# ── update_user 测试 ──


class TestUpdateUser:
    @pytest.mark.asyncio
    async def test_deactivate_user(self):
        """禁用用户."""
        admin = _make_user()
        target = _make_user(is_active=True)
        session = _mock_session(get_result=target)
        data = UserUpdateRequest(is_active=False)

        result = await update_user(target.id, data, admin, session)

        assert result["is_active"] is False

    @pytest.mark.asyncio
    async def test_promote_to_admin(self):
        """设为管理员."""
        admin = _make_user()
        target = _make_user(is_admin=False)
        session = _mock_session(get_result=target)
        data = UserUpdateRequest(is_admin=True)

        result = await update_user(target.id, data, admin, session)

        assert result["is_admin"] is True

    @pytest.mark.asyncio
    async def test_update_user_not_found_returns_404(self):
        """用户不存在 -> 404."""
        admin = _make_user()
        session = _mock_session(get_result=None)
        data = UserUpdateRequest(is_active=False)

        with pytest.raises(HTTPException) as exc_info:
            await update_user(uuid4(), data, admin, session)
        assert exc_info.value.status_code == 404


# ── delete_user 测试 ──


class TestDeleteUser:
    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """删除用户成功."""
        admin = _make_user()
        target = _make_user(username="target")
        session = _mock_session(get_result=target)

        await delete_user(target.id, admin, session)

        session.delete.assert_awaited_once_with(target)

    @pytest.mark.asyncio
    async def test_delete_user_not_found_returns_404(self):
        """用户不存在 -> 404."""
        admin = _make_user()
        session = _mock_session(get_result=None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_user(uuid4(), admin, session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_self_returns_400(self):
        """管理员不能删除自己 -> 400."""
        admin = _make_user()
        session = _mock_session(get_result=admin)

        with pytest.raises(HTTPException) as exc_info:
            await delete_user(admin.id, admin, session)
        assert exc_info.value.status_code == 400


# ── list_experiences 测试 ──


class TestListExperiences:
    @pytest.mark.asyncio
    async def test_list_experiences_success(self):
        """列出所有经验."""
        admin = _make_user()
        exp = _make_experience()
        user = _make_user(username="owner")
        session = _mock_session(all_rows=[(exp, user)], scalar_result=1)

        result = await list_experiences(page=1, page_size=20, admin=admin, session=session)

        assert result["total"] == 1
        assert len(result["items"]) == 1
        assert result["items"][0]["user"]["username"] == "owner"

    @pytest.mark.asyncio
    async def test_list_experiences_null_user(self):
        """经验无归属用户 (user_id=None) -> user 字段为 null."""
        admin = _make_user()
        exp = _make_experience(user_id=None)
        session = _mock_session(all_rows=[(exp, None)], scalar_result=1)

        result = await list_experiences(page=1, page_size=20, admin=admin, session=session)

        assert result["items"][0]["user"] is None


# ── delete_experience 测试 ──


class TestDeleteExperience:
    @pytest.mark.asyncio
    async def test_delete_experience_success(self):
        """删除经验成功."""
        admin = _make_user()
        exp = _make_experience()
        session = _mock_session(get_result=exp)

        await delete_experience(exp.id, admin, session)

        session.delete.assert_awaited_once_with(exp)

    @pytest.mark.asyncio
    async def test_delete_experience_not_found_returns_404(self):
        """经验不存在 -> 404."""
        admin = _make_user()
        session = _mock_session(get_result=None)

        with pytest.raises(HTTPException) as exc_info:
            await delete_experience(uuid4(), admin, session)
        assert exc_info.value.status_code == 404


# ── update_experience_status 测试 ──


class TestUpdateExperienceStatus:
    @pytest.mark.asyncio
    async def test_update_status_success(self):
        """更新经验状态成功."""
        admin = _make_user()
        exp = _make_experience(status="pending")
        session = _mock_session(get_result=exp)
        data = ExperienceStatusUpdate(evaluation_status="approved")

        result = await update_experience_status(exp.id, data, admin, session)

        assert result["evaluation_status"] == "approved"

    @pytest.mark.asyncio
    async def test_update_status_not_found_returns_404(self):
        """经验不存在 -> 404."""
        admin = _make_user()
        session = _mock_session(get_result=None)
        data = ExperienceStatusUpdate(evaluation_status="rejected")

        with pytest.raises(HTTPException) as exc_info:
            await update_experience_status(uuid4(), data, admin, session)
        assert exc_info.value.status_code == 404


# ── list_agents 测试 ──


class TestListAgents:
    @pytest.mark.asyncio
    async def test_list_agents_success(self):
        """列出所有 Agent."""
        admin = _make_user()
        agents = [_make_agent(), _make_agent(name="Agent2")]
        session = _mock_session(scalars_result=agents)

        result = await list_agents(admin, session)

        assert len(result["items"]) == 2
        # api_key 应被截断
        assert result["items"][0]["api_key"].endswith("...")

    @pytest.mark.asyncio
    async def test_list_agents_empty(self):
        """无 Agent -> 空列表."""
        admin = _make_user()
        session = _mock_session(scalars_result=[])

        result = await list_agents(admin, session)

        assert len(result["items"]) == 0


# ── system_stats 测试 ──


class TestSystemStats:
    @pytest.mark.asyncio
    async def test_stats_returns_correct_fields(self):
        """系统统计返回正确的字段结构."""
        admin = _make_user()
        session = _mock_session(scalar_result=5)

        result = await system_stats(admin, session)

        assert "users" in result
        assert "agents" in result
        assert "experiences" in result
        assert "total" in result["users"]
        assert "active" in result["users"]
        assert "admins" in result["users"]
        assert "recent_7d" in result["users"]
        assert "total" in result["agents"]
        assert "active" in result["agents"]
        assert "total" in result["experiences"]
        assert "evaluated" in result["experiences"]
        assert "pending" in result["experiences"]
        assert "recent_7d" in result["experiences"]
