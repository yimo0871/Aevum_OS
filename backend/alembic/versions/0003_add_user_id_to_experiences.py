"""add user_id to experiences

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiences",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_experiences_user_id", "experiences", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_experiences_user_id", table_name="experiences")
    op.drop_column("experiences", "user_id")
