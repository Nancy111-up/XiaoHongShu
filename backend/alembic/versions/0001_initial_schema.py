"""Create the traceable V0.1 database schema."""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = sa.String(length=36)
NOTE_ID = sa.String(length=64)
UTC_DATETIME = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "refresh_jobs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", UTC_DATETIME, nullable=True),
        sa.Column("finished_at", UTC_DATETIME, nullable=True),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
        sa.Column("successful_keywords", sa.Text(), nullable=True),
        sa.Column("failed_keywords", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
    )
    op.create_index("ix_refresh_jobs_status", "refresh_jobs", ["status"])
    op.create_index("ix_refresh_jobs_updated_at", "refresh_jobs", ["updated_at"])

    op.create_table(
        "notes",
        sa.Column("note_id", NOTE_ID, primary_key=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("author_id", sa.String(128), nullable=True),
        sa.Column("author_name", sa.String(256), nullable=True),
        sa.Column("published_at", UTC_DATETIME, nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("first_seen_at", UTC_DATETIME, nullable=False),
        sa.Column("last_seen_at", UTC_DATETIME, nullable=False),
        sa.Column("raw_payload_json", sa.Text(), nullable=False),
    )

    op.create_table(
        "topics",
        sa.Column("topic_id", UUID, primary_key=True),
        sa.Column("canonical_name", sa.String(256), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("first_seen_at", UTC_DATETIME, nullable=False),
        sa.Column("last_seen_at", UTC_DATETIME, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
    )
    op.create_index("ix_topics_last_seen_at", "topics", ["last_seen_at"])

    op.create_table(
        "brand_profiles",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False, unique=True),
        sa.Column("profile_json", sa.Text(), nullable=False),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
    )

    op.create_table(
        "note_snapshots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("refresh_jobs.id"), nullable=False),
        sa.Column("note_id", NOTE_ID, sa.ForeignKey("notes.note_id"), nullable=False),
        sa.Column("captured_at", UTC_DATETIME, nullable=False),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("collects", sa.Integer(), nullable=True),
        sa.Column("comments", sa.Integer(), nullable=True),
        sa.Column("shares", sa.Integer(), nullable=True),
        sa.Column("data_completeness", sa.Float(), nullable=False),
        sa.UniqueConstraint("job_id", "note_id", name="uq_note_snapshots_job_id"),
    )

    op.create_table(
        "note_search_snapshots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("job_id", UUID, sa.ForeignKey("refresh_jobs.id"), nullable=False),
        sa.Column("note_id", NOTE_ID, sa.ForeignKey("notes.note_id"), nullable=False),
        sa.Column("keyword", sa.String(256), nullable=False),
        sa.Column("search_position", sa.Integer(), nullable=False),
        sa.Column("captured_at", UTC_DATETIME, nullable=False),
        sa.UniqueConstraint(
            "job_id", "note_id", "keyword", name="uq_note_search_snapshots_job_id"
        ),
    )

    op.create_table(
        "comments",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("comment_id", sa.String(64), nullable=False),
        sa.Column("note_id", NOTE_ID, sa.ForeignKey("notes.note_id"), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("refresh_jobs.id"), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("likes", sa.Integer(), nullable=True),
        sa.Column("captured_at", UTC_DATETIME, nullable=False),
        sa.UniqueConstraint("job_id", "comment_id", name="uq_comments_job_id"),
    )

    op.create_table(
        "topic_snapshots",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("topic_id", UUID, sa.ForeignKey("topics.topic_id"), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("refresh_jobs.id"), nullable=False),
        sa.Column("captured_at", UTC_DATETIME, nullable=False),
        sa.Column("note_count", sa.Integer(), nullable=False),
        sa.Column("unique_author_count", sa.Integer(), nullable=False),
        sa.Column("comment_sample_count", sa.Integer(), nullable=False),
        sa.Column("raw_metrics_json", sa.Text(), nullable=False),
        sa.Column("normalized_metrics_json", sa.Text(), nullable=False),
        sa.Column("current_heat", sa.Float(), nullable=True),
        sa.Column("trend_score", sa.Float(), nullable=True),
        sa.Column("lifecycle", sa.String(32), nullable=True),
        sa.Column("confidence", sa.String(32), nullable=False),
    )

    op.create_table(
        "topic_snapshot_notes",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "topic_snapshot_id", UUID, sa.ForeignKey("topic_snapshots.id"), nullable=False
        ),
        sa.Column("note_id", NOTE_ID, sa.ForeignKey("notes.note_id"), nullable=False),
        sa.Column("relevance", sa.Float(), nullable=True),
        sa.Column("is_representative", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "topic_snapshot_id", "note_id", name="uq_topic_snapshot_notes_topic_snapshot_id"
        ),
    )

    op.create_table(
        "llm_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("task_type", sa.String(64), nullable=False),
        sa.Column("job_id", UUID, sa.ForeignKey("refresh_jobs.id"), nullable=True),
        sa.Column("topic_id", UUID, sa.ForeignKey("topics.topic_id"), nullable=True),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("input_hash", sa.String(128), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("raw_response", sa.Text(), nullable=True),
        sa.Column("parsed_response", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
    )

    op.create_table(
        "opportunities",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("topic_id", UUID, sa.ForeignKey("topics.topic_id"), nullable=False),
        sa.Column(
            "topic_snapshot_id", UUID, sa.ForeignKey("topic_snapshots.id"), nullable=False
        ),
        sa.Column("job_id", UUID, sa.ForeignKey("refresh_jobs.id"), nullable=False),
        sa.Column("brand_profile_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("decision", sa.String(64), nullable=False),
        sa.Column("eligibility", sa.String(32), nullable=False),
        sa.Column("risk", sa.String(32), nullable=False),
        sa.Column("confidence", sa.String(32), nullable=False),
        sa.Column("goal", sa.String(128), nullable=True),
        sa.Column("score_breakdown_json", sa.Text(), nullable=False),
        sa.Column("reasons_json", sa.Text(), nullable=False),
        sa.Column("recommended_angle", sa.Text(), nullable=True),
        sa.Column("product_connection", sa.Text(), nullable=True),
        sa.Column("copy_preview_json", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
    )
    op.create_index("ix_opportunities_updated_at", "opportunities", ["updated_at"])

    op.create_table(
        "opportunity_llm_runs",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("opportunity_id", UUID, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("llm_run_id", UUID, sa.ForeignKey("llm_runs.id"), nullable=False),
        sa.UniqueConstraint(
            "opportunity_id", "llm_run_id", name="uq_opportunity_llm_runs_opportunity_id"
        ),
    )

    op.create_table(
        "drafts",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "source_opportunity_id", UUID, sa.ForeignKey("opportunities.id"), nullable=False
        ),
        sa.Column("topic_id", UUID, sa.ForeignKey("topics.topic_id"), nullable=False),
        sa.Column("brand_profile_version", sa.Integer(), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("titles_json", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("tags_json", sa.Text(), nullable=False),
        sa.Column("cta", sa.Text(), nullable=True),
        sa.Column("cover_text", sa.Text(), nullable=True),
        sa.Column("image_plan_json", sa.Text(), nullable=False),
        sa.Column("product_connection", sa.Text(), nullable=True),
        sa.Column("risk_check_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
    )

    op.create_table(
        "reject_feedback",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("opportunity_id", UUID, sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("reason", sa.String(64), nullable=False),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
    )

    op.create_table(
        "calendar_items",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("draft_id", UUID, sa.ForeignKey("drafts.id"), nullable=False, unique=True),
        sa.Column("scheduled_for", UTC_DATETIME, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", UTC_DATETIME, nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
    )
    op.create_index("ix_calendar_items_scheduled_for", "calendar_items", ["scheduled_for"])

    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(128), primary_key=True),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("updated_at", UTC_DATETIME, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_index("ix_calendar_items_scheduled_for", table_name="calendar_items")
    op.drop_table("calendar_items")
    op.drop_table("reject_feedback")
    op.drop_table("drafts")
    op.drop_table("opportunity_llm_runs")
    op.drop_index("ix_opportunities_updated_at", table_name="opportunities")
    op.drop_table("opportunities")
    op.drop_table("llm_runs")
    op.drop_table("topic_snapshot_notes")
    op.drop_table("topic_snapshots")
    op.drop_table("comments")
    op.drop_table("note_search_snapshots")
    op.drop_table("note_snapshots")
    op.drop_table("brand_profiles")
    op.drop_index("ix_topics_last_seen_at", table_name="topics")
    op.drop_table("topics")
    op.drop_table("notes")
    op.drop_index("ix_refresh_jobs_updated_at", table_name="refresh_jobs")
    op.drop_index("ix_refresh_jobs_status", table_name="refresh_jobs")
    op.drop_table("refresh_jobs")
