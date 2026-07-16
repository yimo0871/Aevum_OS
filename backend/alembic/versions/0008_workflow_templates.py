"""create workflow_templates table

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "workflow_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("domain", sa.String(100), nullable=False, index=True),
        sa.Column("task_type", sa.String(100), nullable=False, index=True),
        sa.Column("steps", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tools", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("expected_outcome", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("success_rate", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("usage_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("visibility", sa.String(20), nullable=False, server_default="public", index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workflow_templates")
