"""Enforce one active refresh job at a time."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_single_active_refresh"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ACTIVE_STATUS_PREDICATE = (
    "status IN ('queued', 'collecting_search', 'collecting_detail', "
    "'normalizing', 'clustering', 'enriching', 'scoring_trend', "
    "'scoring_opportunity', 'generating_preview')"
)


def upgrade() -> None:
    op.add_column("refresh_jobs", sa.Column("active_slot", sa.String(length=16), nullable=True))
    op.execute(
        "UPDATE refresh_jobs SET active_slot = 'active' WHERE " + _ACTIVE_STATUS_PREDICATE
    )
    op.create_index(
        "uq_refresh_jobs_single_active",
        "refresh_jobs",
        ["active_slot"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_refresh_jobs_single_active", table_name="refresh_jobs")
    op.drop_column("refresh_jobs", "active_slot")
