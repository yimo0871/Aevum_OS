"""add world_bridges table

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "world_bridges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("bridge_type", sa.String(20), nullable=False, index=True),
        sa.Column("human_expression_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("human_expressions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("experience_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_by", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("bridge_type", "human_expression_id", "experience_id", name="uq_bridge_type_expr_exp"),
    )


def downgrade() -> None:
    op.drop_table("world_bridges")
