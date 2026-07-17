"""Marketplace service - 经验交易市场业务逻辑."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.experience import Experience
from app.models.marketplace import ExperienceListing, Transaction
from app.schemas.marketplace import ListingCreate

logger = logging.getLogger(__name__)


class MarketplaceService:
    """经验交易市场服务.

    职责:
    - 创建/浏览/下架经验挂单
    - 处理经验购买交易
    - 查询用户的购买和销售记录
    """

    async def create_listing(
        self,
        experience_id: UUID,
        seller_id: UUID,
        data: ListingCreate,
        session: AsyncSession,
    ) -> ExperienceListing:
        """创建经验挂单.

        Args:
            experience_id: 经验 ID
            seller_id: 卖家用户 ID
            data: 挂单创建数据
            session: 异步数据库会话

        Returns:
            创建的 ExperienceListing 对象

        Raises:
            ValueError: 经验不存在
        """
        experience = await session.get(Experience, experience_id)
        if experience is None:
            raise ValueError(f"经验不存在: {experience_id}")

        listing = ExperienceListing(
            experience_id=experience_id,
            seller_id=seller_id,
            title=data.title,
            description=data.description,
            price=data.price,
            currency=data.currency,
            license_type=data.license_type,
            status="active",
        )
        session.add(listing)
        await session.flush()
        await session.refresh(listing)

        logger.info(
            "[MARKETPLACE] 挂单已创建: listing_id=%s, experience_id=%s, seller=%s, price=%.2f",
            listing.id, experience_id, seller_id, data.price,
        )
        return listing

    async def list_listings(
        self,
        page: int = 1,
        page_size: int = 20,
        domain: str | None = None,
        license_type: str | None = None,
        min_price: float | None = None,
        max_price: float | None = None,
        session: AsyncSession | None = None,
    ) -> tuple[list[ExperienceListing], int]:
        """浏览挂单列表（分页 + 过滤）.

        Args:
            page: 页码
            page_size: 每页数量
            domain: 领域过滤（通过关联经验的 context.domain）
            license_type: 许可类型过滤
            min_price: 最低价格
            max_price: 最高价格
            session: 异步数据库会话

        Returns:
            (listings, total_count)
        """
        query = select(ExperienceListing).where(ExperienceListing.status == "active")

        if domain:
            query = query.join(
                Experience, ExperienceListing.experience_id == Experience.id
            ).where(Experience.context["domain"].astext == domain)

        if license_type:
            query = query.where(ExperienceListing.license_type == license_type)
        if min_price is not None:
            query = query.where(ExperienceListing.price >= min_price)
        if max_price is not None:
            query = query.where(ExperienceListing.price <= max_price)

        # ── 总数 ──
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0

        # ── 分页 ──
        offset = (page - 1) * page_size
        query = query.order_by(ExperienceListing.created_at.desc()).offset(offset).limit(page_size)
        result = await session.execute(query)
        listings = list(result.scalars().all())

        return listings, total

    async def get_listing(
        self, listing_id: UUID, session: AsyncSession
    ) -> ExperienceListing | None:
        """获取挂单详情.

        Args:
            listing_id: 挂单 ID
            session: 异步数据库会话

        Returns:
            ExperienceListing 对象或 None
        """
        result = await session.execute(
            select(ExperienceListing).where(ExperienceListing.id == listing_id)
        )
        return result.scalar_one_or_none()

    async def purchase(
        self, listing_id: UUID, buyer_id: UUID, session: AsyncSession
    ) -> tuple[Transaction, ExperienceListing]:
        """购买挂单 - 创建交易并标记挂单为已售出.

        Args:
            listing_id: 挂单 ID
            buyer_id: 买家用户 ID
            session: 异步数据库会话

        Returns:
            (transaction, listing) 元组

        Raises:
            ValueError: 挂单不存在、挂单不可购买、买家是卖家
        """
        listing = await self.get_listing(listing_id, session)
        if listing is None:
            raise ValueError(f"挂单不存在: {listing_id}")

        if listing.status != "active":
            raise ValueError(f"挂单状态为 {listing.status}，不可购买")

        if listing.seller_id == buyer_id:
            raise ValueError("不能购买自己的挂单")

        now = datetime.now(timezone.utc)
        transaction = Transaction(
            listing_id=listing_id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            amount=listing.price,
            currency=listing.currency,
            status="completed",
            completed_at=now,
        )
        session.add(transaction)

        # 标记挂单为已售出
        listing.status = "sold"

        await session.flush()
        await session.refresh(transaction)
        await session.refresh(listing)

        logger.info(
            "[MARKETPLACE] 交易完成: transaction_id=%s, listing_id=%s, buyer=%s, amount=%.2f",
            transaction.id, listing_id, buyer_id, transaction.amount,
        )
        return transaction, listing

    async def delist(
        self, listing_id: UUID, seller_id: UUID, session: AsyncSession
    ) -> ExperienceListing:
        """下架挂单（仅卖家可操作）.

        Args:
            listing_id: 挂单 ID
            seller_id: 卖家用户 ID
            session: 异步数据库会话

        Returns:
            更新后的 ExperienceListing 对象

        Raises:
            ValueError: 挂单不存在、无权操作
        """
        listing = await self.get_listing(listing_id, session)
        if listing is None:
            raise ValueError(f"挂单不存在: {listing_id}")

        if listing.seller_id != seller_id:
            raise ValueError("无权下架他人的挂单")

        listing.status = "delisted"
        await session.flush()
        await session.refresh(listing)

        logger.info(
            "[MARKETPLACE] 挂单已下架: listing_id=%s, seller=%s",
            listing_id, seller_id,
        )
        return listing

    async def get_user_purchases(
        self, buyer_id: UUID, session: AsyncSession
    ) -> list[Transaction]:
        """获取用户的购买记录.

        Args:
            buyer_id: 买家用户 ID
            session: 异步数据库会话

        Returns:
            交易记录列表（按时间倒序）
        """
        query = (
            select(Transaction)
            .where(Transaction.buyer_id == buyer_id)
            .order_by(Transaction.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_user_sales(
        self, seller_id: UUID, session: AsyncSession
    ) -> list[Transaction]:
        """获取用户的销售记录.

        Args:
            seller_id: 卖家用户 ID
            session: 异步数据库会话

        Returns:
            交易记录列表（按时间倒序）
        """
        query = (
            select(Transaction)
            .where(Transaction.seller_id == seller_id)
            .order_by(Transaction.created_at.desc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())
