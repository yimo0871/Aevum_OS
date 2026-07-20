"""治理层 visibility 权限校验单元测试.

确保 fork/improve/cite 操作不会绕过经验的 visibility 权限隔离。
- private 经验: 仅创建者可 fork/improve/cite
- community 经验: 同社区成员可访问
- public 经验: 任何人可访问
"""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.v1.governance import _assert_experience_accessible


def _make_experience(user_id, visibility="private", community_id=None):
    """创建模拟 Experience 对象."""
    exp = MagicMock()
    exp.user_id = user_id
    exp.visibility = visibility
    exp.community_id = community_id
    return exp


def _make_user(user_id):
    """创建模拟 User 对象."""
    user = MagicMock()
    user.id = user_id
    return user


class TestAssertExperienceAccessible:
    """测试 _assert_experience_accessible 权限校验函数."""

    @pytest.mark.asyncio
    async def test_owner_can_access_own_private(self):
        """经验创建者可以访问自己的 private 经验."""
        uid = uuid4()
        exp = _make_experience(user_id=uid, visibility="private")
        user = _make_user(uid)
        session = AsyncMock()

        # 不应抛出异常
        await _assert_experience_accessible(exp, user, session)

    @pytest.mark.asyncio
    async def test_other_user_cannot_access_private(self):
        """其他用户无法访问 private 经验 -> 403."""
        exp = _make_experience(user_id=uuid4(), visibility="private")
        user = _make_user(uuid4())
        session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await _assert_experience_accessible(exp, user, session)
        assert exc_info.value.status_code == 403
        assert "私有" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_anyone_can_access_public(self):
        """任何用户可以访问 public 经验."""
        exp = _make_experience(user_id=uuid4(), visibility="public")
        user = _make_user(uuid4())
        session = AsyncMock()

        # 不应抛出异常
        await _assert_experience_accessible(exp, user, session)

    @pytest.mark.asyncio
    async def test_anonymous_user_can_access_public(self):
        """匿名场景: user_id 不匹配但 public 仍可访问."""
        exp = _make_experience(user_id=uuid4(), visibility="public")
        user = _make_user(uuid4())
        session = AsyncMock()

        await _assert_experience_accessible(exp, user, session)

    @pytest.mark.asyncio
    async def test_community_member_can_access_community(self):
        """同社区成员可以访问 community 经验."""
        cid = uuid4()
        exp = _make_experience(user_id=uuid4(), visibility="community", community_id=cid)
        user = _make_user(uuid4())
        session = AsyncMock()

        # 模拟数据库查询返回用户是该社区成员
        mock_result = MagicMock()
        mock_result.fetchone.return_value = (cid,)
        session.execute = AsyncMock(return_value=mock_result)

        await _assert_experience_accessible(exp, user, session)

    @pytest.mark.asyncio
    async def test_non_community_member_cannot_access_community(self):
        """非同社区成员无法访问 community 经验 -> 403."""
        cid = uuid4()
        exp = _make_experience(user_id=uuid4(), visibility="community", community_id=cid)
        user = _make_user(uuid4())
        session = AsyncMock()

        # 模拟数据库查询返回空（用户不是社区成员）
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await _assert_experience_accessible(exp, user, session)
        assert exc_info.value.status_code == 403
        assert "社区" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_community_without_community_id_is_inaccessible(self):
        """community 经验但没有 community_id -> 403（防御性处理）."""
        exp = _make_experience(user_id=uuid4(), visibility="community", community_id=None)
        user = _make_user(uuid4())
        session = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await _assert_experience_accessible(exp, user, session)
        assert exc_info.value.status_code == 403


class TestForkVisibilityEnforcement:
    """测试 fork API 端点的 visibility 权限校验."""

    @pytest.mark.asyncio
    async def test_fork_private_experience_of_other_user_returns_403(self):
        """fork 他人的 private 经验应返回 403."""
        from app.api.v1.governance import fork_experience

        owner_id = uuid4()
        attacker_id = uuid4()
        exp_id = uuid4()

        # 模拟源经验（private，属于 owner）
        source_exp = _make_experience(user_id=owner_id, visibility="private")
        source_exp.id = exp_id

        session = AsyncMock()
        session.get = AsyncMock(return_value=source_exp)

        attacker = _make_user(attacker_id)

        with pytest.raises(HTTPException) as exc_info:
            await fork_experience(exp_id, attacker, session)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_fork_own_private_experience_succeeds(self):
        """fork 自己的 private 经验应成功（通过权限校验）."""
        from app.api.v1.governance import fork_experience

        owner_id = uuid4()
        exp_id = uuid4()

        source_exp = _make_experience(user_id=owner_id, visibility="private")
        source_exp.id = exp_id
        source_exp.to_dict.return_value = {"id": str(exp_id)}

        session = AsyncMock()
        session.get = AsyncMock(return_value=source_exp)

        owner = _make_user(owner_id)

        # mock VersionManager.fork
        forked_exp = MagicMock()
        forked_exp.id = uuid4()
        forked_exp.to_dict.return_value = {"id": "forked"}

        with patch("app.api.v1.governance.VersionManager") as MockVM:
            MockVM.return_value.fork = AsyncMock(return_value=forked_exp)
            result = await fork_experience(exp_id, owner, session)

        assert "forked_experience" in result
        assert result["source_id"] == str(exp_id)

    @pytest.mark.asyncio
    async def test_fork_public_experience_of_other_user_succeeds(self):
        """fork 他人的 public 经验应成功（通过权限校验）."""
        from app.api.v1.governance import fork_experience

        owner_id = uuid4()
        attacker_id = uuid4()
        exp_id = uuid4()

        source_exp = _make_experience(user_id=owner_id, visibility="public")
        source_exp.id = exp_id

        session = AsyncMock()
        session.get = AsyncMock(return_value=source_exp)

        attacker = _make_user(attacker_id)

        forked_exp = MagicMock()
        forked_exp.id = uuid4()
        forked_exp.to_dict.return_value = {"id": "forked"}

        with patch("app.api.v1.governance.VersionManager") as MockVM:
            MockVM.return_value.fork = AsyncMock(return_value=forked_exp)
            result = await fork_experience(exp_id, attacker, session)

        assert "forked_experience" in result


class TestImproveVisibilityEnforcement:
    """测试 improve API 端点的 visibility 权限校验."""

    @pytest.mark.asyncio
    async def test_improve_private_experience_of_other_user_returns_403(self):
        """improve 他人的 private 经验应返回 403."""
        from app.api.v1.governance import improve_experience, ImproveRequest

        owner_id = uuid4()
        attacker_id = uuid4()
        exp_id = uuid4()

        source_exp = _make_experience(user_id=owner_id, visibility="private")
        source_exp.id = exp_id

        session = AsyncMock()
        session.get = AsyncMock(return_value=source_exp)

        attacker = _make_user(attacker_id)
        request = ImproveRequest(improvements={"intent": "改进版"})

        with pytest.raises(HTTPException) as exc_info:
            await improve_experience(exp_id, request, attacker, session)

        assert exc_info.value.status_code == 403


class TestCiteVisibilityEnforcement:
    """测试 cite API 端点的 visibility 权限校验."""

    @pytest.mark.asyncio
    async def test_cite_private_target_returns_403(self):
        """cite 他人的 private 经验（作为被引用方）应返回 403."""
        from app.api.v1.governance import cite_experience, CiteRequest

        owner_id = uuid4()
        attacker_id = uuid4()
        target_id = uuid4()
        citing_id = uuid4()

        # 被引用的 private 经验（属于 owner）
        target_exp = _make_experience(user_id=owner_id, visibility="private")
        target_exp.id = target_id

        # 引用方经验（属于 attacker）
        citing_exp = _make_experience(user_id=attacker_id, visibility="private")
        citing_exp.id = citing_id

        session = AsyncMock()
        session.get = AsyncMock(side_effect=[target_exp, citing_exp])

        attacker = _make_user(attacker_id)
        request = CiteRequest(citing_experience_id=citing_id)

        with pytest.raises(HTTPException) as exc_info:
            await cite_experience(target_id, request, attacker, session)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_cite_private_citing_of_other_user_returns_403(self):
        """cite 时引用方经验属于他人且 private 应返回 403."""
        from app.api.v1.governance import cite_experience, CiteRequest

        attacker_id = uuid4()
        other_id = uuid4()
        target_id = uuid4()
        citing_id = uuid4()

        # 被引用的 public 经验
        target_exp = _make_experience(user_id=other_id, visibility="public")
        target_exp.id = target_id

        # 引用方 private 经验属于 other（不是 attacker）
        citing_exp = _make_experience(user_id=other_id, visibility="private")
        citing_exp.id = citing_id

        session = AsyncMock()
        session.get = AsyncMock(side_effect=[target_exp, citing_exp])

        attacker = _make_user(attacker_id)
        request = CiteRequest(citing_experience_id=citing_id)

        with pytest.raises(HTTPException) as exc_info:
            await cite_experience(target_id, request, attacker, session)

        assert exc_info.value.status_code == 403
