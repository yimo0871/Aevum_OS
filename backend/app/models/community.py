"""Community ORM 模型 - 社区与用户关联."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, String, Table, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


# ── 用户-社区多对多关联表 ──
user_community = Table(
    "user_community",
    Base.metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("community_id", UUID(as_uuid=True), ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(20), nullable=False, default="member"),  # member / moderator / admin
    Column("joined_at", DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False),
    UniqueConstraint("user_id", "community_id", name="uq_user_community"),
)


class Community(Base):
    """社区模型."""

    __tablename__ = "communities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, index=True)
    description = Column(Text, default="")
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    # open: 自由加入 / invite: 仅邀请
    visibility = Column(String(20), nullable=False, default="open", server_default="open")
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Community(id={self.id}, name={self.name})>"
