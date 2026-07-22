"""sport taxonomy (swim CSS pace) + workout press_lap flag

Adds athletes.css_pace_s_per_100m (drives swim training zones) and
workouts.press_lap (drives the "- Press lap" structured_text prefix).
The athlete/workout sport enum itself (cycling|running|swimming|
cross_country_skiing|weight_training, replacing triathlon) is enforced at
the Pydantic schema layer only — both columns were already a plain
String(32), so no DDL change is needed for that part.

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-22
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("athletes", sa.Column("css_pace_s_per_100m", sa.Float, nullable=True))
    op.add_column(
        "workouts",
        sa.Column("press_lap", sa.Boolean, nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("workouts", "press_lap")
    op.drop_column("athletes", "css_pace_s_per_100m")
