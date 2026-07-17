"""Agent ORM 模型 - 注册的外部 Agent."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class Agent(Base):
    """Agent 模型 - 注册的外部 Agent，通过 API Key 认证."""

    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    api_key = Column(String(255), unique=True, nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    capabilities = Column(JSONB, default=dict)
    created_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_active_at = Column(DateTime(timezone=True), nullable=True)

    # ── 去中心化身份 (DID) ──
    did = Column(String(255), nullable=True, index=True)
    # ── 所有者名称（人类可读）──
    owner_name = Column(String(200), nullable=True)

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name={self.name})>"
