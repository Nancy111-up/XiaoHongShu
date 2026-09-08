"""Ensure refresh failure summaries remain nullable on existing databases."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_refresh_error_summary"
down_revision: str | None = "0002_single_active_refresh"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("refresh_jobs")}
    if "error_summary" not in columns:
        op.add_column("refresh_jobs", sa.Column("error_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    # The initial schema already owns this optional column, so retain it when
    # rolling back this compatibility repair.
    pass
