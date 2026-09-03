from __future__ import annotations

import sys
from pathlib import Path

import pytest

from src.crawler.adapter import MediaCrawlerAdapter
from src.crawler.settings import MediaCrawlerSettings


@pytest.fixture
def settings(tmp_path: Path) -> MediaCrawlerSettings:
    return MediaCrawlerSettings(
        checkout_path=tmp_path / "MediaCrawler",
        python_executable="python",
    )


def test_search_command_disables_comments_and_limits_raw_notes(
    settings: MediaCrawlerSettings,
) -> None:
    command = MediaCrawlerAdapter(settings).build_search_command("校园足球", Path("raw"))

    joined = " ".join(command)
    assert "--platform xhs" in joined
    assert "--type search" in joined
    assert "--get_comment false" in joined
    assert "--crawler_max_notes_count 40" in joined
    assert "--max_concurrency_num 1" in joined
    assert "--save_data_option jsonl" in joined
    assert "--cookies" not in joined


def test_detail_command_only_fetches_first_level_comments(
    settings: MediaCrawlerSettings,
) -> None:
    command = MediaCrawlerAdapter(settings).build_detail_command(["n1", "n2"], Path("detail"))

    joined = " ".join(command)
    assert "--type detail" in joined
    assert "--get_comment true" in joined
    assert "--get_sub_comment false" in joined
    assert "--max_comments_count_singlenotes 20" in joined
    assert "--max_concurrency_num 1" in joined


def test_detail_command_rejects_an_empty_note_list(settings: MediaCrawlerSettings) -> None:
    with pytest.raises(ValueError, match="at least one note"):
        MediaCrawlerAdapter(settings).build_detail_command([], Path("detail"))


@pytest.mark.asyncio
async def test_run_captures_exit_metadata_and_redacts_cookie_values(tmp_path: Path) -> None:
    checkout_path = tmp_path / "MediaCrawler"
    checkout_path.mkdir()
    (checkout_path / "fake_main.py").write_text(
        "import sys\n"
        "print('Cookie: session=top-secret; xsec_token=also-secret', file=sys.stderr)\n"
        "raise SystemExit(7)\n",
        encoding="utf-8",
    )
    settings = MediaCrawlerSettings(
        checkout_path=checkout_path,
        python_executable=sys.executable,
        runner_args=("fake_main.py",),
    )
    raw_path = tmp_path / "raw" / "job-1"

    execution = await MediaCrawlerAdapter(settings).run_search("校园足球", raw_path)

    assert execution.exit_code == 7
    assert execution.started_at.tzinfo is not None
    assert execution.finished_at >= execution.started_at
    assert execution.raw_path == raw_path.resolve()
    assert execution.raw_path.is_dir()
    assert execution.stderr_summary is not None
    assert "top-secret" not in execution.stderr_summary
    assert "also-secret" not in execution.stderr_summary
    assert "Cookie: [REDACTED]" in execution.stderr_summary
