"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-15
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "athletes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervals_user_id", sa.String(64), nullable=False),
        sa.Column("strava_athlete_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sport", sa.String(32), nullable=False),
        sa.Column("ftp_watts", sa.Integer, nullable=True),
        sa.Column("threshold_pace_s_per_m", sa.Float, nullable=True),
        sa.Column("lthr", sa.Integer, nullable=True),
        sa.Column("max_hr", sa.Integer, nullable=True),
        sa.Column("resting_hr", sa.Integer, nullable=True),
        sa.Column("weight_kg", sa.Float, nullable=True),
        sa.Column("vo2max", sa.Float, nullable=True),
        sa.Column("training_zones", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("intervals_api_key_encrypted", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intervals_user_id"),
    )

    op.create_table(
        "strava_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("access_token_encrypted", sa.Text, nullable=False),
        sa.Column("refresh_token_encrypted", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scope", sa.Text, nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("athlete_id"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
    )

    op.create_table(
        "routes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sport", sa.String(32), nullable=False),
        sa.Column("gpx_data", sa.Text, nullable=True),
        sa.Column("distance_m", sa.Float, nullable=False),
        sa.Column("elevation_gain_m", sa.Float, nullable=False),
        sa.Column("elevation_loss_m", sa.Float, nullable=False),
        sa.Column("max_elevation_m", sa.Float, nullable=True),
        sa.Column("min_elevation_m", sa.Float, nullable=True),
        sa.Column("climb_profile", postgresql.JSONB, nullable=False, server_default="[]"),
        sa.Column("terrain_score", sa.Float, nullable=True),
        sa.Column("surface_type", sa.String(32), nullable=True),
        sa.Column("analysis", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_routes_athlete_id", "routes", ["athlete_id"])

    op.create_table(
        "workouts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("route_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("intervals_workout_id", sa.String(64), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sport", sa.String(32), nullable=False),
        sa.Column("workout_type", sa.String(64), nullable=False),
        sa.Column("scheduled_date", sa.Date, nullable=True),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("target_tss", sa.Float, nullable=True),
        sa.Column("structured_text", sa.Text, nullable=True),
        sa.Column("llm_plan", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("llm_reasoning", sa.Text, nullable=True),
        sa.Column("coach_notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["route_id"], ["routes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_workouts_athlete_id", "workouts", ["athlete_id"])
    op.create_index("ix_workouts_scheduled_date", "workouts", ["scheduled_date"])

    op.create_table(
        "training_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("intervals_activity_id", sa.String(64), nullable=False),
        sa.Column("sport", sa.String(32), nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("distance_m", sa.Float, nullable=True),
        sa.Column("avg_power_watts", sa.Float, nullable=True),
        sa.Column("normalized_power_watts", sa.Float, nullable=True),
        sa.Column("avg_hr", sa.Integer, nullable=True),
        sa.Column("max_hr", sa.Integer, nullable=True),
        sa.Column("tss", sa.Float, nullable=True),
        sa.Column("intensity_factor", sa.Float, nullable=True),
        sa.Column("elevation_gain_m", sa.Float, nullable=True),
        sa.Column("avg_speed_kmh", sa.Float, nullable=True),
        sa.Column("activity_data", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("intervals_activity_id"),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_training_sessions_athlete_id", "training_sessions", ["athlete_id"])
    op.create_index("ix_training_sessions_start_date", "training_sessions", ["start_date"])

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("document_title", sa.Text, nullable=False),
        sa.Column("document_source", sa.Text, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text, nullable=True),  # stored as vector via pgvector
        sa.Column("metadata", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_id", "chunk_index", name="uq_document_chunk"),
    )

    # Alter embedding column to actual vector type after pgvector extension is active
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(768) USING NULL")

    # IVFFlat ANN index for cosine similarity
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("document_chunks")
    op.drop_table("training_sessions")
    op.drop_table("workouts")
    op.drop_table("routes")
    op.drop_table("strava_tokens")
    op.drop_table("athletes")
