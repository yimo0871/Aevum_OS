"""add visibility column to experiences

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "experiences",
        sa.Column(
            "visibility",
            sa.String(20),
            nullable=False,
            server_default="private",
        ),
    )
    op.create_index("ix_experiences_visibility", "experiences", ["visibility"])

    # ── 数据迁移：保留已有行为的兼容性 ──
    # user_id 为 NULL 的旧数据视为公开（维持原有全局可见行为）
    # user_id 不为 NULL 的旧数据设为私有（安全默认值）
    op.execute(
        "UPDATE experiences SET visibility = 'public' WHERE user_id IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_experiences_visibility", table_name="experiences")
    op.drop_column("experiences", "visibility")
