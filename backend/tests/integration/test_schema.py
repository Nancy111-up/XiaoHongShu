from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, inspect

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TABLES = {
    "refresh_jobs",
    "notes",
    "note_snapshots",
    "note_search_snapshots",
    "topics",
    "topic_snapshots",
    "topic_snapshot_notes",
    "comments",
    "llm_runs",
    "brand_profiles",
    "opportunities",
    "opportunity_llm_runs",
    "drafts",
    "reject_feedback",
    "calendar_items",
    "system_settings",
}


@contextmanager
def _migrated_engine(tmp_path: Path) -> Iterator[Engine]:
    database_path = tmp_path / "schema.sqlite3"
    config_path = BACKEND_ROOT / "alembic.ini"
    assert config_path.is_file(), "Alembic migration configuration is missing"
    config = Config(str(config_path))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{database_path.as_posix()}")
    yield engine
    engine.dispose()


def _unique_column_sets(engine: Engine, table: str) -> set[frozenset[str]]:
    return {
        frozenset(constraint["column_names"])
        for constraint in inspect(engine).get_unique_constraints(table)
    }


def test_initial_migration_matches_model_metadata(tmp_path: Path) -> None:
    database_path = tmp_path / "metadata-check.sqlite3"
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{database_path.as_posix()}")
    command.upgrade(config, "head")
    command.check(config)


def test_initial_migration_creates_required_tables_and_uniques(tmp_path: Path) -> None:
    with _migrated_engine(tmp_path) as migrated_engine:
        assert set(inspect(migrated_engine).get_table_names()) >= EXPECTED_TABLES
        assert frozenset({"job_id", "note_id"}) in _unique_column_sets(
            migrated_engine, "note_snapshots"
        )
        assert frozenset({"job_id", "note_id", "keyword"}) in _unique_column_sets(
            migrated_engine, "note_search_snapshots"
        )
        assert frozenset({"topic_snapshot_id", "note_id"}) in _unique_column_sets(
            migrated_engine, "topic_snapshot_notes"
        )


@pytest.mark.parametrize(
    ("table", "column"),
    [
        ("refresh_jobs", "status"),
        ("refresh_jobs", "updated_at"),
        ("topics", "last_seen_at"),
        ("opportunities", "updated_at"),
        ("calendar_items", "scheduled_for"),
    ],
)
def test_initial_migration_indexes_operational_queries(
    tmp_path: Path, table: str, column: str
) -> None:
    with _migrated_engine(tmp_path) as migrated_engine:
        indexed_columns = {
            indexed_column
            for index in inspect(migrated_engine).get_indexes(table)
            for indexed_column in index["column_names"]
        }
        assert column in indexed_columns
