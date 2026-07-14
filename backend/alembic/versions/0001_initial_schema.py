"""initial schema with pgvector

Revision ID: 0001
Revises:
Create Date: 2026-07-14

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enable pgvector extension ──
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ── experiences table ──
    op.create_table(
        "experiences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("context", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("intent", sa.Text, nullable=False),
        sa.Column("execution", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("outcome", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("reflection", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("reusable_patterns", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("confidence_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("provenance", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("evaluation_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── Add embedding column (pgvector) ──
    op.execute("ALTER TABLE experiences ADD COLUMN embedding vector(1536)")

    # ── Indexes for experiences ──
    op.create_index("ix_experiences_timestamp", "experiences", ["timestamp"])
    op.create_index("ix_experiences_confidence_score", "experiences", ["confidence_score"])
    op.create_index("ix_experiences_evaluation_status", "experiences", ["evaluation_status"])
    # GIN index for JSONB context (for domain/task_type filtering)
    op.execute(
        "CREATE INDEX ix_experiences_context_gin ON experiences USING GIN (context jsonb_path_ops)"
    )
    # HNSW index for vector similarity search
    op.execute(
        "CREATE INDEX ix_experiences_embedding_hnsw ON experiences "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )

    # ── experience_relations table ──
    op.create_table(
        "experience_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiences.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relation_type", sa.String(20), nullable=False),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_experience_relations_source_id", "experience_relations", ["source_id"])
    op.create_index("ix_experience_relations_target_id", "experience_relations", ["target_id"])
    op.create_index("ix_experience_relations_type", "experience_relations", ["relation_type"])

    # ── execution_traces table ──
    op.create_table(
        "execution_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("experience_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("experiences.id", ondelete="CASCADE"), nullable=True),
        sa.Column("intent", sa.Text, nullable=False),
        sa.Column("context", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("steps", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("tools", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("trace", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("duration", sa.Float, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("pipeline_state", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_execution_traces_status", "execution_traces", ["status"])
    op.create_index("ix_execution_traces_experience_id", "execution_traces", ["experience_id"])

    # ── evaluations table ──
    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("target_type", sa.String(20), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evaluator", sa.String(50), nullable=False),
        sa.Column("scores", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("overall_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("details", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_evaluations_target", "evaluations", ["target_type", "target_id"])

    # ── system_metrics table ──
    op.create_table(
        "system_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("metric_name", sa.String(50), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
    )
    op.create_index("ix_system_metrics_name", "system_metrics", ["metric_name"])
    op.create_index("ix_system_metrics_timestamp", "system_metrics", ["timestamp"])


def downgrade() -> None:
    op.drop_table("system_metrics")
    op.drop_table("evaluations")
    op.drop_table("execution_traces")
    op.drop_table("experience_relations")
    op.drop_index("ix_experiences_embedding_hnsw", table_name="experiences")
    op.drop_index("ix_experiences_context_gin", table_name="experiences")
    op.drop_table("experiences")
