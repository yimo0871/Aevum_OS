"""performance indexes for high-frequency queries.

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade():
    # 经验检索高频查询路径：user_id + visibility + created_at
    op.create_index(
        "ix_experiences_user_visibility_created",
        "experiences",
        ["user_id", "visibility", "created_at"],
    )
    # 评估状态过滤
    op.create_index(
        "ix_experiences_evaluation_status_created",
        "experiences",
        ["evaluation_status", "created_at"],
    )
    # 经验关系表：target_id + relation_type（复用计数查询）
    op.create_index(
        "ix_experience_relations_target_type",
        "experience_relations",
        ["target_id", "relation_type"],
    )
    # 市场上架查询：status + created_at
    op.create_index(
        "ix_experience_listings_status_created",
        "experience_listings",
        ["status", "created_at"],
    )
    # 全文检索索引（支持混合检索的 BM25 部分）
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_experiences_intent_fts "
        "ON experiences USING gin(to_tsvector('simple', coalesce(intent, '') || ' ' || coalesce(context->>'domain', '')))"
    )


def downgrade():
    op.drop_index("ix_experiences_intent_fts", table_name="experiences")
    op.drop_index("ix_experience_listings_status_created", table_name="experience_listings")
    op.drop_index("ix_experience_relations_target_type", table_name="experience_relations")
    op.drop_index("ix_experiences_evaluation_status_created", table_name="experiences")
    op.drop_index("ix_experiences_user_visibility_created", table_name="experiences")
