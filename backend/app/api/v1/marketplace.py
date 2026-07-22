"""Marketplace API routes - 经验交易市场."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db_session, get_optional_user
from app.models.user import User
from app.schemas.marketplace import (
    ListingCreate,
    ListingListResponse,
    ListingResponse,
    PurchaseResponse,
    TransactionListResponse,
    TransactionResponse,
)
from app.services.marketplace.marketplace_service import MarketplaceService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/listings",
    response_model=ListingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建挂单",
    description="将一条经验发布到交易市场进行出售。",
)
async def create_listing(
    data: ListingCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ListingResponse:
    service = MarketplaceService()
    try:
        listing = await service.create_listing(
            experience_id=data.experience_id,
            seller_id=current_user.id,
            data=data,
            session=session,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return ListingResponse.model_validate(listing)


@router.get(
    "/listings",
    response_model=ListingListResponse,
    summary="浏览挂单",
    description="分页浏览交易市场中的活跃挂单，支持按领域、许可类型、价格过滤。",
)
async def list_listings(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    domain: str | None = Query(None, description="领域过滤"),
    license_type: str | None = Query(None, description="许可类型过滤"),
    min_price: float | None = Query(None, ge=0.0, description="最低价格"),
    max_price: float | None = Query(None, ge=0.0, description="最高价格"),
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> ListingListResponse:
    service = MarketplaceService()
    listings, total = await service.list_listings(
        page=page,
        page_size=page_size,
        domain=domain,
        license_type=license_type,
        min_price=min_price,
        max_price=max_price,
        session=session,
    )
    return ListingListResponse(
        items=[ListingResponse.model_validate(l) for l in listings],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/listings/{listing_id}",
    response_model=ListingResponse,
    summary="获取挂单详情",
    description="根据 ID 获取单个挂单详情。",
)
async def get_listing(
    listing_id: UUID,
    current_user: User | None = Depends(get_optional_user),
    session: AsyncSession = Depends(get_db_session),
) -> ListingResponse:
    service = MarketplaceService()
    listing = await service.get_listing(listing_id, session)
    if listing is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"挂单 {listing_id} 不存在")
    return ListingResponse.model_validate(listing)


@router.post(
    "/listings/{listing_id}/purchase",
    response_model=PurchaseResponse,
    summary="购买挂单",
    description="购买一条经验挂单，创建交易并标记挂单为已售出。",
)
async def purchase_listing(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> PurchaseResponse:
    service = MarketplaceService()
    try:
        transaction, listing = await service.purchase(
            listing_id=listing_id,
            buyer_id=current_user.id,
            session=session,
        )
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return PurchaseResponse(
        transaction=TransactionResponse.model_validate(transaction),
        listing_status=listing.status,
    )


@router.delete(
    "/listings/{listing_id}",
    response_model=ListingResponse,
    summary="下架挂单",
    description="卖家下架自己的挂单。",
)
async def delist_listing(
    listing_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> ListingResponse:
    service = MarketplaceService()
    try:
        listing = await service.delist(
            listing_id=listing_id,
            seller_id=current_user.id,
            session=session,
        )
    except ValueError as e:
        if "不存在" in str(e):
            raise HTTPException(status.HTTP_404_NOT_FOUND, str(e))
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(e))
    return ListingResponse.model_validate(listing)


@router.get(
    "/purchases",
    response_model=TransactionListResponse,
    summary="我的购买记录",
    description="获取当前用户的购买交易记录。",
)
async def my_purchases(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TransactionListResponse:
    service = MarketplaceService()
    transactions = await service.get_user_purchases(current_user.id, session)
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=len(transactions),
        page=1,
        page_size=len(transactions),
    )


@router.get(
    "/sales",
    response_model=TransactionListResponse,
    summary="我的销售记录",
    description="获取当前用户的销售交易记录。",
)
async def my_sales(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> TransactionListResponse:
    service = MarketplaceService()
    transactions = await service.get_user_sales(current_user.id, session)
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=len(transactions),
        page=1,
        page_size=len(transactions),
    )
