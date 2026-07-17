"""create human_reviews table

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "human_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "experience_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("experiences.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer, nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("recommend_archive", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_human_reviews_experience_id", "human_reviews", ["experience_id"])
    op.create_index("ix_human_reviews_reviewer_id", "human_reviews", ["reviewer_id"])


def downgrade() -> None:
    op.drop_index("ix_human_reviews_reviewer_id", table_name="human_reviews")
    op.drop_index("ix_human_reviews_experience_id", table_name="human_reviews")
    op.drop_table("human_reviews")
