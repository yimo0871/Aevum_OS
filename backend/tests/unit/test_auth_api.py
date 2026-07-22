"""auth API 路由单元测试.

覆盖端点:
- POST /auth/register  (注册成功 / 重复409)
- POST /auth/login     (登录成功 / 错误密码401 / 禁用403)
- GET  /auth/me        (已认证返回用户)
- PUT  /auth/me        (更新用户名 / 重复用户名409)
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException

from app.api.v1.auth import register, login, get_me, update_me
from app.schemas.user import UserCreate, UserLogin, UserUpdate


def _make_user(
    uid=None,
    email="test@example.com",
    username="testuser",
    hashed_password="$2b$12$fakehash",
    is_active=True,
    is_admin=False,
    bio="",
):
    """创建模拟 User 对象."""
    user = MagicMock()
    user.id = uid or uuid4()
    user.email = email
    user.username = username
    user.hashed_password = hashed_password
    user.is_active = is_active
    user.is_admin = is_admin
    user.bio = bio
    user.created_at = datetime.now(timezone.utc)
    user.updated_at = datetime.now(timezone.utc)
    return user


def _mock_session(scalar_result=None, scalars_result=None):
    """创建模拟 AsyncSession."""
    session = AsyncMock()
    result = MagicMock()
    if scalar_result is not None:
        result.scalar_one_or_none.return_value = scalar_result
    if scalars_result is not None:
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = scalars_result
        result.scalars.return_value = scalars_mock
    session.execute.return_value = result
    session.flush = AsyncMock()
    session.add = MagicMock()
    return session


# ── register 测试 ──


class TestRegister:
    @pytest.mark.asyncio
    async def test_register_success(self):
        """注册成功 -> 返回 Token."""
        session = _mock_session(scalar_result=None)
        data = UserCreate(
            email="new@example.com", username="newuser", password="strongpass123"
        )

        with patch("app.api.v1.auth.get_password_hash", return_value="hashed"):
            with patch("app.api.v1.auth.create_access_token", return_value="jwt-token"):
                token = await register(data, session)

        assert token.access_token == "jwt-token"
        assert token.user.email == "new@example.com"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self):
        """重复邮箱 -> 409."""
        existing = _make_user(email="dup@example.com", username="other")
        session = _mock_session(scalar_result=existing)
        data = UserCreate(
            email="dup@example.com", username="newuser", password="strongpass123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await register(data, session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_register_duplicate_username_returns_409(self):
        """重复用户名 -> 409."""
        existing = _make_user(email="other@example.com", username="dupname")
        session = _mock_session(scalar_result=existing)
        data = UserCreate(
            email="new@example.com", username="dupname", password="strongpass123"
        )

        with pytest.raises(HTTPException) as exc_info:
            await register(data, session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_register_short_password_raises_validation_error(self):
        """密码太短 -> Pydantic 验证错误 (min_length=8)."""
        with pytest.raises(Exception):
            UserCreate(email="a@b.com", username="user", password="short")


# ── login 测试 ──


class TestLogin:
    @pytest.mark.asyncio
    async def test_login_success(self):
        """登录成功 -> 返回 Token."""
        user = _make_user(username="testuser", hashed_password="$2b$12$hash")
        session = _mock_session(scalar_result=user)
        data = UserLogin(username="testuser", password="strongpass123")

        with patch("app.api.v1.auth.verify_password", return_value=True):
            with patch("app.api.v1.auth.create_access_token", return_value="jwt-token"):
                token = await login(data, session)

        assert token.access_token == "jwt-token"
        assert token.user.username == "testuser"

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self):
        """密码错误 -> 401."""
        user = _make_user(hashed_password="$2b$12$hash")
        session = _mock_session(scalar_result=user)
        data = UserLogin(username="testuser", password="wrongpassword")

        with patch("app.api.v1.auth.verify_password", return_value=False):
            with pytest.raises(HTTPException) as exc_info:
                await login(data, session)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user_returns_401(self):
        """用户不存在 -> 401."""
        session = _mock_session(scalar_result=None)
        data = UserLogin(username="nouser", password="somepassword")

        with pytest.raises(HTTPException) as exc_info:
            await login(data, session)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_login_disabled_user_returns_403(self):
        """被禁用的用户 -> 403."""
        user = _make_user(is_active=False)
        session = _mock_session(scalar_result=user)
        data = UserLogin(username="testuser", password="strongpass123")

        with patch("app.api.v1.auth.verify_password", return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await login(data, session)
        assert exc_info.value.status_code == 403


# ── get_me 测试 ──


class TestGetMe:
    @pytest.mark.asyncio
    async def test_get_me_returns_current_user(self):
        """已认证用户 -> 返回用户信息."""
        user = _make_user(username="myuser")
        response = await get_me(current_user=user)
        assert response.username == "myuser"
        assert response.email == "test@example.com"


# ── update_me 测试 ──


class TestUpdateMe:
    @pytest.mark.asyncio
    async def test_update_username_success(self):
        """更新用户名成功."""
        user = _make_user(username="oldname")
        session = _mock_session(scalar_result=None)
        data = UserUpdate(username="newname")

        result = await update_me(data, user, session)
        assert result.username == "newname"
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_username_duplicate_returns_409(self):
        """用户名已被占用 -> 409."""
        user = _make_user(username="oldname")
        existing = _make_user(username="takenname")
        session = _mock_session(scalar_result=existing)
        data = UserUpdate(username="takenname")

        with pytest.raises(HTTPException) as exc_info:
            await update_me(data, user, session)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_update_bio_success(self):
        """更新个人简介成功."""
        user = _make_user(bio="old bio")
        session = _mock_session(scalar_result=None)
        data = UserUpdate(bio="new bio")

        result = await update_me(data, user, session)
        assert result.bio == "new bio"

    @pytest.mark.asyncio
    async def test_update_same_username_no_conflict(self):
        """用户名未变更时不检查冲突."""
        user = _make_user(username="sameuser")
        session = _mock_session(scalar_result=None)
        data = UserUpdate(username="sameuser")

        result = await update_me(data, user, session)
        assert result.username == "sameuser"
