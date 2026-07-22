"""Unit tests for MarketplaceService and models - 经验交易市场."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.experience import Experience
from app.models.marketplace import ExperienceListing, Transaction
from app.schemas.marketplace import ListingCreate
from app.services.marketplace.marketplace_service import MarketplaceService


# ── Helpers ──


def _make_experience(**overrides) -> Experience:
    """Build an Experience ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
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
    )
    defaults.update(overrides)
    return Experience(**defaults)


def _make_listing(**overrides) -> ExperienceListing:
    """Build an ExperienceListing ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        experience_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        title="DevOps Best Practices",
        description="A collection of DevOps experiences",
        price=9.99,
        currency="USD",
        license_type="paid",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return ExperienceListing(**defaults)


def _make_transaction(**overrides) -> Transaction:
    """Build a Transaction ORM object for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        listing_id=uuid.uuid4(),
        buyer_id=uuid.uuid4(),
        seller_id=uuid.uuid4(),
        amount=9.99,
        currency="USD",
        status="completed",
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Transaction(**defaults)


def _make_mock_session(get_return=None) -> AsyncMock:
    """Build a mock async session where .get returns get_return."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=get_return)
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ── Model tests ──


class TestExperienceListingModel:
    """Test ExperienceListing ORM model."""

    def test_creation(self) -> None:
        listing = _make_listing(title="My Listing", price=19.99)
        assert listing.title == "My Listing"
        assert listing.price == 19.99

    def test_defaults(self) -> None:
        listing = ExperienceListing(
            experience_id=uuid.uuid4(),
            seller_id=uuid.uuid4(),
            title="Test",
        )
        # Defaults are applied at flush/commit time, not at instantiation
        assert listing.title == "Test"
        assert listing.experience_id is not None

    def test_repr(self) -> None:
        listing = _make_listing(title="TestListing")
        assert "TestListing" in repr(listing)

    def test_to_dict(self) -> None:
        listing = _make_listing()
        d = listing.to_dict()
        assert d["title"] == "DevOps Best Practices"
        assert d["price"] == 9.99
        assert d["id"] == str(listing.id)
        assert d["experience_id"] == str(listing.experience_id)
        assert "created_at" in d


class TestTransactionModel:
    """Test Transaction ORM model."""

    def test_creation(self) -> None:
        tx = _make_transaction(amount=50.0, status="pending")
        assert tx.amount == 50.0
        assert tx.status == "pending"

    def test_repr(self) -> None:
        tx = _make_transaction(amount=5.0)
        assert "5.0" in repr(tx)

    def test_to_dict(self) -> None:
        tx = _make_transaction()
        d = tx.to_dict()
        assert d["amount"] == 9.99
        assert d["status"] == "completed"
        assert d["id"] == str(tx.id)
        assert d["buyer_id"] == str(tx.buyer_id)
        assert "completed_at" in d


# ── create_listing tests ──


class TestCreateListing:
    """Test MarketplaceService.create_listing."""

    @pytest.mark.asyncio
    async def test_create_listing_success(self) -> None:
        exp = _make_experience()
        session = _make_mock_session(get_return=exp)

        service = MarketplaceService()
        data = ListingCreate(
            experience_id=exp.id,
            title="Test Listing",
            price=15.0,
            license_type="paid",
        )
        result = await service.create_listing(exp.id, exp.user_id, data, session)

        session.add.assert_called_once()
        assert result.title == "Test Listing"
        assert result.price == 15.0
        assert result.status == "active"

    @pytest.mark.asyncio
    async def test_create_listing_free_default(self) -> None:
        exp = _make_experience()
        session = _make_mock_session(get_return=exp)

        service = MarketplaceService()
        data = ListingCreate(experience_id=exp.id, title="Free Listing")
        result = await service.create_listing(exp.id, exp.user_id, data, session)

        assert result.price == 0.0
        assert result.license_type == "free"

    @pytest.mark.asyncio
    async def test_create_listing_experience_not_found_raises(self) -> None:
        session = _make_mock_session(get_return=None)

        service = MarketplaceService()
        data = ListingCreate(experience_id=uuid.uuid4(), title="Test")
        with pytest.raises(ValueError, match="经验不存在"):
            await service.create_listing(uuid.uuid4(), uuid.uuid4(), data, session)


# ── get_listing tests ──


class TestGetListing:
    """Test MarketplaceService.get_listing."""

    @pytest.mark.asyncio
    async def test_get_listing_found(self) -> None:
        listing = _make_listing()
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        result = await service.get_listing(listing.id, session)

        assert result is listing

    @pytest.mark.asyncio
    async def test_get_listing_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        result = await service.get_listing(uuid.uuid4(), session)

        assert result is None


# ── purchase tests ──


class TestPurchase:
    """Test MarketplaceService.purchase."""

    @pytest.mark.asyncio
    async def test_purchase_success(self) -> None:
        seller_id = uuid.uuid4()
        buyer_id = uuid.uuid4()
        listing = _make_listing(seller_id=seller_id, price=25.0, status="active")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        service = MarketplaceService()
        tx, updated_listing = await service.purchase(listing.id, buyer_id, session)

        assert tx.amount == 25.0
        assert tx.buyer_id == buyer_id
        assert tx.seller_id == seller_id
        assert tx.status == "completed"
        assert updated_listing.status == "sold"
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_purchase_listing_not_found_raises(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        with pytest.raises(ValueError, match="挂单不存在"):
            await service.purchase(uuid.uuid4(), uuid.uuid4(), session)

    @pytest.mark.asyncio
    async def test_purchase_already_sold_raises(self) -> None:
        listing = _make_listing(status="sold")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        with pytest.raises(ValueError, match="不可购买"):
            await service.purchase(listing.id, uuid.uuid4(), session)

    @pytest.mark.asyncio
    async def test_purchase_self_raises(self) -> None:
        seller_id = uuid.uuid4()
        listing = _make_listing(seller_id=seller_id, status="active")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        with pytest.raises(ValueError, match="不能购买自己"):
            await service.purchase(listing.id, seller_id, session)


# ── delist tests ──


class TestDelist:
    """Test MarketplaceService.delist."""

    @pytest.mark.asyncio
    async def test_delist_success(self) -> None:
        seller_id = uuid.uuid4()
        listing = _make_listing(seller_id=seller_id, status="active")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        service = MarketplaceService()
        result = await service.delist(listing.id, seller_id, session)

        assert result.status == "delisted"

    @pytest.mark.asyncio
    async def test_delist_not_owner_raises(self) -> None:
        seller_id = uuid.uuid4()
        other_id = uuid.uuid4()
        listing = _make_listing(seller_id=seller_id, status="active")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        with pytest.raises(ValueError, match="无权下架"):
            await service.delist(listing.id, other_id, session)

    @pytest.mark.asyncio
    async def test_delist_not_found_raises(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        with pytest.raises(ValueError, match="挂单不存在"):
            await service.delist(uuid.uuid4(), uuid.uuid4(), session)


# ── get_user_purchases / get_user_sales tests ──


class TestUserTransactions:
    """Test MarketplaceService.get_user_purchases and get_user_sales."""

    @pytest.mark.asyncio
    async def test_get_user_purchases(self) -> None:
        buyer_id = uuid.uuid4()
        txs = [_make_transaction(buyer_id=buyer_id), _make_transaction(buyer_id=buyer_id)]
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = txs
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        result = await service.get_user_purchases(buyer_id, session)

        assert len(result) == 2
        assert result == txs

    @pytest.mark.asyncio
    async def test_get_user_purchases_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        result = await service.get_user_purchases(uuid.uuid4(), session)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_sales(self) -> None:
        seller_id = uuid.uuid4()
        txs = [_make_transaction(seller_id=seller_id), _make_transaction(seller_id=seller_id)]
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = txs
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        result = await service.get_user_sales(seller_id, session)

        assert len(result) == 2
        assert result == txs

    @pytest.mark.asyncio
    async def test_get_user_sales_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        result = await service.get_user_sales(uuid.uuid4(), session)

        assert result == []


# ── list_listings tests ──


class TestListListings:
    """Test MarketplaceService.list_listings."""

    @pytest.mark.asyncio
    async def test_list_listings_returns_results(self) -> None:
        listings = [_make_listing(), _make_listing()]
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 2
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = listings
        session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = MarketplaceService()
        result, total = await service.list_listings(page=1, page_size=20, session=session)

        assert total == 2
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_listings_empty(self) -> None:
        session = AsyncMock()
        count_result = MagicMock()
        count_result.scalar.return_value = 0
        list_result = MagicMock()
        list_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(side_effect=[count_result, list_result])

        service = MarketplaceService()
        result, total = await service.list_listings(session=session)

        assert total == 0
        assert result == []


# ── Ownership verification tests ──


class TestCreateListingOwnership:
    """Test ownership verification in MarketplaceService.create_listing."""

    @pytest.mark.asyncio
    async def test_create_listing_not_owner_raises(self) -> None:
        """非经验所有者不能创建挂单."""
        owner_id = uuid.uuid4()
        attacker_id = uuid.uuid4()
        exp = _make_experience(user_id=owner_id)
        session = _make_mock_session(get_return=exp)

        service = MarketplaceService()
        data = ListingCreate(experience_id=exp.id, title="Stolen Listing", price=10.0)
        with pytest.raises(ValueError, match="无权出售他人的经验"):
            await service.create_listing(exp.id, attacker_id, data, session)

    @pytest.mark.asyncio
    async def test_create_listing_owner_succeeds(self) -> None:
        """经验所有者可以创建挂单."""
        owner_id = uuid.uuid4()
        exp = _make_experience(user_id=owner_id)
        session = _make_mock_session(get_return=exp)

        service = MarketplaceService()
        data = ListingCreate(experience_id=exp.id, title="My Listing", price=20.0)
        result = await service.create_listing(exp.id, owner_id, data, session)

        assert result.seller_id == owner_id
        assert result.title == "My Listing"

    @pytest.mark.asyncio
    async def test_create_listing_experience_with_null_user_id_raises(self) -> None:
        """经验无归属用户（user_id=None）时不能创建挂单."""
        exp = _make_experience(user_id=None)
        session = _make_mock_session(get_return=exp)

        service = MarketplaceService()
        data = ListingCreate(experience_id=exp.id, title="Orphan Listing")
        with pytest.raises(ValueError, match="无权出售他人的经验"):
            await service.create_listing(exp.id, uuid.uuid4(), data, session)


# ── Purchase race condition tests ──


class TestPurchaseRaceCondition:
    """Test race condition handling in MarketplaceService.purchase."""

    @pytest.mark.asyncio
    async def test_purchase_uses_row_lock(self) -> None:
        """验证 purchase 使用行级锁 (with_for_update)."""
        seller_id = uuid.uuid4()
        buyer_id = uuid.uuid4()
        listing = _make_listing(seller_id=seller_id, status="active")

        # 捕获 execute 调用的参数，验证 with_for_update 被调用
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)
        session.flush = AsyncMock()

        service = MarketplaceService()
        await service.purchase(listing.id, buyer_id, session)

        # 验证 execute 被调用
        assert session.execute.called
        # 检查传入的 SQL 是否包含 FOR UPDATE
        call_args = session.execute.call_args
        # with_for_update() 会修改 SQL 语句对象，我们验证它被调用过
        # 由于使用的是 SQLAlchemy select().with_for_update()，结果 SQL 应包含 FOR UPDATE
        executed_stmt = call_args[0][0] if call_args[0] else call_args[1].get("statement")
        if executed_stmt is not None:
            compiled = str(executed_stmt.compile(compile_kwargs={"literal_binds": True}))
            assert "FOR UPDATE" in compiled, f"Expected FOR UPDATE in query, got: {compiled}"

    @pytest.mark.asyncio
    async def test_purchase_concurrent_second_buyer_sees_sold(self) -> None:
        """模拟并发购买：第二个买家看到 status=sold 时应报错."""
        seller_id = uuid.uuid4()
        buyer1_id = uuid.uuid4()
        buyer2_id = uuid.uuid4()

        # 第一个买家购买时挂单是 active
        listing_active = _make_listing(seller_id=seller_id, status="active")
        # 第二个买家查询时挂单已变为 sold（模拟行级锁释放后的状态）
        listing_sold = _make_listing(seller_id=seller_id, status="sold")

        # 第一次 purchase 返回 active 挂单
        session1 = AsyncMock()
        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = listing_active
        session1.execute = AsyncMock(return_value=result1)
        session1.flush = AsyncMock()

        # 第二次 purchase 返回 sold 挂单
        session2 = AsyncMock()
        result2 = MagicMock()
        result2.scalar_one_or_none.return_value = listing_sold
        session2.execute = AsyncMock(return_value=result2)
        session2.flush = AsyncMock()

        service = MarketplaceService()

        # 第一个买家成功购买
        tx1, updated1 = await service.purchase(listing_active.id, buyer1_id, session1)
        assert updated1.status == "sold"
        assert tx1.buyer_id == buyer1_id

        # 第二个买家购买失败（挂单已 sold）
        with pytest.raises(ValueError, match="不可购买"):
            await service.purchase(listing_sold.id, buyer2_id, session2)

    @pytest.mark.asyncio
    async def test_purchase_delisted_listing_raises(self) -> None:
        """已下架挂单不可购买."""
        listing = _make_listing(status="delisted")
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = listing
        session.execute = AsyncMock(return_value=result_mock)

        service = MarketplaceService()
        with pytest.raises(ValueError, match="不可购买"):
            await service.purchase(listing.id, uuid.uuid4(), session)
