"""multi-user auth: add users/user_settings/system_settings, drop Strava

This is a breaking schema change (fresh-start decision): athletes.user_id is
added as NOT NULL with no backfill path, and Strava integration is removed
entirely in favor of intervals.icu as the sole external integration. Deploy
against a fresh/empty database — do not run against a populated prototype DB.

Revision ID: 0003
Revises: 27bcb0eaaca9
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "27bcb0eaaca9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(16), nullable=False, server_default="user"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("must_change_password", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "user_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "key", name="uq_user_settings_user_key"),
    )

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("value", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_secret", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("key"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
    )

    # --- Strava removal ---
    op.drop_table("strava_tokens")
    op.drop_column("athletes", "strava_athlete_id")

    # --- Link athletes to users (fresh-start: no backfill) ---
    op.add_column("athletes", sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False))
    op.create_unique_constraint("uq_athletes_user_id", "athletes", ["user_id"])
    op.create_foreign_key(
        "fk_athletes_user_id_users", "athletes", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("fk_athletes_user_id_users", "athletes", type_="foreignkey")
    op.drop_constraint("uq_athletes_user_id", "athletes", type_="unique")
    op.drop_column("athletes", "user_id")

    op.add_column("athletes", sa.Column("strava_athlete_id", sa.String(64), nullable=True))
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

    op.drop_table("system_settings")
    op.drop_table("user_settings")
    op.drop_table("users")
