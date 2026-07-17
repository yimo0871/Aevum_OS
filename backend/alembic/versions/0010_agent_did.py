"""add agent did/owner_name and experience owner_agent_id/status/compressed columns

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── agents: 添加 did 与 owner_name ──
    op.add_column("agents", sa.Column("did", sa.String(255), nullable=True))
    op.add_column("agents", sa.Column("owner_name", sa.String(200), nullable=True))
    op.create_index("ix_agents_did", "agents", ["did"], unique=False)

    # ── experiences: 添加 owner_agent_id 外键 ──
    op.add_column(
        "experiences",
        sa.Column(
            "owner_agent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agents.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_experiences_owner_agent_id", "experiences", ["owner_agent_id"])

    # ── experiences: 添加 status / compressed / compression_summary（压缩与遗忘支持）──
    op.add_column(
        "experiences",
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="active",
        ),
    )
    op.add_column(
        "experiences",
        sa.Column(
            "compressed",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "experiences",
        sa.Column("compression_summary", sa.Text, nullable=True),
    )
    op.create_index("ix_experiences_status", "experiences", ["status"])
    op.create_index("ix_experiences_compressed", "experiences", ["compressed"])


def downgrade() -> None:
    op.drop_index("ix_experiences_compressed", table_name="experiences")
    op.drop_index("ix_experiences_status", table_name="experiences")
    op.drop_column("experiences", "compression_summary")
    op.drop_column("experiences", "compressed")
    op.drop_column("experiences", "status")
    op.drop_index("ix_experiences_owner_agent_id", table_name="experiences")
    op.drop_column("experiences", "owner_agent_id")
    op.drop_index("ix_agents_did", table_name="agents")
    op.drop_column("agents", "owner_name")
    op.drop_column("agents", "did")
