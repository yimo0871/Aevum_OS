"""create cocreation_sessions table

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cocreation_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("task_description", sa.Text, nullable=False),
        sa.Column("domain", sa.String(100), nullable=True),
        sa.Column(
            "human_constraints",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("agent_proposals", postgresql.JSONB, nullable=True),
        sa.Column("human_feedback", sa.Text, nullable=True),
        sa.Column("human_rating", sa.Integer, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="defined"),
        sa.Column(
            "experience_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiences.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_cocreation_sessions_user_id", "cocreation_sessions", ["user_id"])
    op.create_index("ix_cocreation_sessions_status", "cocreation_sessions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_cocreation_sessions_status", table_name="cocreation_sessions")
    op.drop_index("ix_cocreation_sessions_user_id", table_name="cocreation_sessions")
    op.drop_table("cocreation_sessions")
