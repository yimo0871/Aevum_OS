"""change embedding dimension to 2048 for doubao-embedding-vision

Revision ID: 0014
Revises: 0013
Create Date: 2026-07-20
"""

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 删除旧索引
    op.execute("DROP INDEX IF EXISTS ix_experiences_embedding_hnsw")
    # 清空现有 embedding 数据（维度不兼容，需重新生成）
    op.execute("UPDATE experiences SET embedding = NULL")
    op.execute("UPDATE human_expressions SET embedding = NULL")
    # 修改列维度为 1024（doubao-embedding-vision 降维，HNSW 最大 2000）
    op.execute("ALTER TABLE experiences ALTER COLUMN embedding TYPE vector(1024)")
    op.execute("ALTER TABLE human_expressions ALTER COLUMN embedding TYPE vector(1024)")
    # 重建 HNSW 索引
    op.execute(
        "CREATE INDEX ix_experiences_embedding_hnsw ON experiences "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_experiences_embedding_hnsw")
    op.execute("UPDATE experiences SET embedding = NULL")
    op.execute("UPDATE human_expressions SET embedding = NULL")
    op.execute("ALTER TABLE experiences ALTER COLUMN embedding TYPE vector(1536)")
    op.execute("ALTER TABLE human_expressions ALTER COLUMN embedding TYPE vector(1536)")
    op.execute(
        "CREATE INDEX ix_experiences_embedding_hnsw ON experiences "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
