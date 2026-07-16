"""add communities tables and experience.community_id

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── communities 表 ──
    op.create_table(
        "communities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, index=True),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # ── user_community 关联表 ──
    op.create_table(
        "user_community",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("community_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communities.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column("joined_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "community_id", name="uq_user_community"),
    )
    op.create_index("ix_user_community_community_id", "user_community", ["community_id"])

    # ── experiences 添加 community_id ──
    op.add_column(
        "experiences",
        sa.Column("community_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communities.id"), nullable=True),
    )
    op.create_index("ix_experiences_community_id", "experiences", ["community_id"])


def downgrade() -> None:
    op.drop_index("ix_experiences_community_id", table_name="experiences")
    op.drop_column("experiences", "community_id")
    op.drop_index("ix_user_community_community_id", table_name="user_community")
    op.drop_table("user_community")
    op.drop_table("communities")
