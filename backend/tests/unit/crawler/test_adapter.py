from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.crawler.adapter import MediaCrawlerAdapter, _summarize_stderr
from src.crawler.settings import MediaCrawlerSettings


@pytest.fixture
def settings(tmp_path: Path) -> MediaCrawlerSettings:
    return MediaCrawlerSettings(checkout_path=tmp_path / "MediaCrawler", python_executable="python")


def test_search_command_disables_comments_and_limits_raw_notes(
    settings: MediaCrawlerSettings,
) -> None:
    joined = " ".join(MediaCrawlerAdapter(settings).build_search_command("校园足球", Path("raw")))
    assert "--platform xhs" in joined
    assert "--type search" in joined
    assert "--get_comment false" in joined
    assert "--crawler_max_notes_count 40" in joined
    assert "--max_concurrency_num 1" in joined
    assert "--save_data_option jsonl" in joined
    assert "--cookies" not in joined


def test_detail_command_only_fetches_first_level_comments(settings: MediaCrawlerSettings) -> None:
    signed_target = (
        "https://www.xiaohongshu.com/explore/n1?xsec_token=private-token&xsec_source=pc_search"
    )
    joined = " ".join(
        MediaCrawlerAdapter(settings).build_detail_command([signed_target, "n2"], Path("detail"))
    )
    assert "--type detail" in joined
    assert "--get_comment true" in joined
    assert "--get_sub_comment false" in joined
    assert "--max_comments_count_singlenotes 20" in joined
    assert "--max_concurrency_num 1" in joined
    assert f"--specified_id {signed_target},n2" in joined


@pytest.mark.parametrize("note_ids", [[], [""], [" ", "\t"]])
def test_detail_command_rejects_empty_note_ids(
    settings: MediaCrawlerSettings, note_ids: list[str]
) -> None:
    with pytest.raises(ValueError, match="at least one note"):
        MediaCrawlerAdapter(settings).build_detail_command(note_ids, Path("detail"))


def test_detail_command_rejects_comma_inside_a_detail_target(
    settings: MediaCrawlerSettings,
) -> None:
    with pytest.raises(ValueError, match="comma"):
        MediaCrawlerAdapter(settings).build_detail_command(
            [
                "https://www.xiaohongshu.com/explore/n1"
                "?xsec_token=token,foreign-id&xsec_source=pc_search"
            ],
            Path("detail"),
        )


@pytest.mark.parametrize(
    ("stderr", "secrets"),
    [
        ("{'xsec_token': 'dict-secret'}", ["dict-secret"]),
        ('{"Cookie": "json-secret"}', ["json-secret"]),
        (
            "{'Cookie': 'sid=dict-first; web_session=dict-tail'}",
            ["dict-first", "dict-tail"],
        ),
        (
            '{"Cookie": "sid=json-first; web_session=json-tail"}',
            ["json-first", "json-tail"],
        ),
        ("Authorization: Bearer bearer-secret", ["bearer-secret"]),
        ("set-cookie: sid=cookie-secret; Path=/", ["cookie-secret"]),
        ("XsEc_ToKeN=MiXeD-secret", ["MiXeD-secret"]),
        (
            "notice\nCookie: first-secret\nAuthorization=Bearer second-secret\nend",
            ["first-secret", "second-secret"],
        ),
    ],
)
def test_stderr_summary_redacts_all_secret_forms(stderr: str, secrets: list[str]) -> None:
    summary = _summarize_stderr(stderr.encode())
    assert summary is not None
    assert "[REDACTED]" in summary
    for secret in secrets:
        assert secret not in summary


@pytest.mark.asyncio
async def test_run_captures_exit_metadata_without_leaking_multiline_secrets(tmp_path: Path) -> None:
    checkout_path = tmp_path / "MediaCrawler"
    checkout_path.mkdir()
    (checkout_path / "fake_main.py").write_text(
        "import sys\nprint(\"{'xsec_token': 'dict-secret'}\", file=sys.stderr)\n"
        "print('Authorization: Bearer bearer-secret', file=sys.stderr)\nraise SystemExit(7)\n",
        encoding="utf-8",
    )
    settings = MediaCrawlerSettings(
        checkout_path=checkout_path, python_executable=sys.executable, runner_args=("fake_main.py",)
    )
    raw_path = tmp_path / "raw" / "job-1"
    execution = await MediaCrawlerAdapter(settings).run_search("校园足球", raw_path)
    assert execution.exit_code == 7
    assert execution.started_at.tzinfo is not None
    assert execution.finished_at >= execution.started_at
    assert execution.raw_path == raw_path.resolve()
    assert execution.raw_path.is_dir()
    assert execution.stderr_summary is not None
    assert "dict-secret" not in execution.stderr_summary
    assert "bearer-secret" not in execution.stderr_summary


def _git(checkout: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=checkout, check=True, capture_output=True, text=True
    ).stdout.strip()


def _checkout(tmp_path: Path, origin: str) -> tuple[Path, str]:
    checkout = tmp_path / "MediaCrawler"
    checkout.mkdir()
    _git(checkout, "init")
    _git(checkout, "config", "user.email", "test@example.com")
    _git(checkout, "config", "user.name", "Test User")
    (checkout / "tracked.txt").write_text("one", encoding="utf-8")
    _git(checkout, "add", "tracked.txt")
    _git(checkout, "commit", "-m", "first")
    _git(checkout, "remote", "add", "origin", origin)
    return checkout, _git(checkout, "rev-parse", "HEAD")


@pytest.mark.parametrize(
    "origin",
    [
        "https://github.com/NanmiCoder/MediaCrawler",
        "https://github.com/NanmiCoder/MediaCrawler.git",
        "https://github.com/NanmiCoder/MediaCrawler.git/",
        "git@github.com:NanmiCoder/MediaCrawler.git",
        "ssh://git@github.com/NanmiCoder/MediaCrawler.git",
    ],
)
def test_checkout_accepts_only_canonical_official_origin_variants(
    tmp_path: Path, origin: str
) -> None:
    checkout, commit = _checkout(tmp_path, origin)
    MediaCrawlerSettings(checkout_path=checkout, commit=commit).verify_checkout()


@pytest.mark.parametrize(
    "origin",
    [
        "http://github.com/NanmiCoder/MediaCrawler.git",
        "https://github.com/OtherOwner/MediaCrawler.git",
        "https://github.com/NanmiCoder/OtherRepo.git",
    ],
)
def test_checkout_rejects_insecure_or_foreign_origins(tmp_path: Path, origin: str) -> None:
    checkout, commit = _checkout(tmp_path, origin)
    with pytest.raises(RuntimeError, match="origin"):
        MediaCrawlerSettings(checkout_path=checkout, commit=commit).verify_checkout()


def test_checkout_rejects_wrong_head(tmp_path: Path) -> None:
    checkout, pinned = _checkout(tmp_path, "https://github.com/NanmiCoder/MediaCrawler.git")
    (checkout / "tracked.txt").write_text("two", encoding="utf-8")
    _git(checkout, "commit", "-am", "second")
    with pytest.raises(RuntimeError, match="HEAD"):
        MediaCrawlerSettings(checkout_path=checkout, commit=pinned).verify_checkout()


def test_checkout_rejects_dirty_tracked_tree(tmp_path: Path) -> None:
    checkout, commit = _checkout(tmp_path, "https://github.com/NanmiCoder/MediaCrawler.git")
    (checkout / "tracked.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(RuntimeError, match="dirty"):
        MediaCrawlerSettings(checkout_path=checkout, commit=commit).verify_checkout()


def test_checkout_rejects_dirty_untracked_tree(tmp_path: Path) -> None:
    checkout, commit = _checkout(tmp_path, "https://github.com/NanmiCoder/MediaCrawler.git")
    (checkout / "untracked.txt").write_text("dirty", encoding="utf-8")
    with pytest.raises(RuntimeError, match="dirty"):
        MediaCrawlerSettings(checkout_path=checkout, commit=commit).verify_checkout()


def test_checkout_rejects_missing_checkout(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="missing"):
        MediaCrawlerSettings(checkout_path=tmp_path / "missing").verify_checkout()
