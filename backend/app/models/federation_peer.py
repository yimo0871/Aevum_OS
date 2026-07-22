"""Federation peer model - 联邦对等节点持久化模型."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FederationPeer(Base):
    """联邦对等节点 - 持久化已注册的远程 Aevum 节点信息.

    服务重启后可通过数据库恢复对等节点列表。
    """

    __tablename__ = "federation_peers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<FederationPeer(id={self.id}, url={self.url})>"
