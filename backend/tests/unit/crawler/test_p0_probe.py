from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest

from scripts import p0_mediacrawler_probe as probe
from src.crawler.adapter import CrawlExecution
from src.crawler.settings import MediaCrawlerSettings

RUN_ID = "2d03ba34dfb943578c26dd90cb7ef67c"
KEYWORDS = ("校园足球", "足球装备", "大学生体育")


def _write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def _note(note_id: str, comments: list[dict[str, object]] | None = None) -> dict[str, object]:
    note: dict[str, object] = {
        "note_id": note_id,
        "note_url": (
            f"https://www.xiaohongshu.com/explore/{note_id}"
            "?xsec_token=test-token&xsec_source=pc_search"
        ),
    }
    note["comments" if comments is not None else "comment_count"] = (
        comments if comments is not None else 4
    )
    return note


def _comment(comment_id: str, note_id: str, parent_comment_id: str = "") -> dict[str, object]:
    return {
        "comment_id": comment_id,
        "note_id": note_id,
        "content": "x",
        "parent_comment_id": parent_comment_id,
    }


def _job(
    root: Path,
    name: str,
    mode: str,
    notes: list[dict[str, object]],
    *,
    run_id: str = RUN_ID,
    keyword: str | None = None,
    note_ids: object | None = None,
) -> Path:
    path = root / name
    path.mkdir()
    started = datetime.now(UTC) - timedelta(minutes=2)
    finished = started + timedelta(minutes=1)
    manifest: dict[str, object] = {
        "run_id": run_id,
        "mode": mode,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        "exit_code": 0,
        "raw_path": str(path.resolve()),
    }
    if keyword is not None:
        manifest["keyword"] = keyword
    if note_ids is not None:
        manifest["note_ids"] = note_ids
    _write_json(path / "manifest.json", manifest)
    (path / "notes.jsonl").write_text(
        "\n".join(json.dumps(note) for note in notes), encoding="utf-8"
    )
    return path


def _valid_tree(root: Path, comments: list[dict[str, object]] | None = None) -> None:
    _write_json(
        root / "run.json",
        {
            "run_id": RUN_ID,
            "started_at": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            "finished_at": datetime.now(UTC).isoformat(),
            "status": "completed",
        },
    )
    for index, keyword in enumerate(KEYWORDS, 1):
        _job(root, f"search-{index}", "search", [_note(f"s{index}")], keyword=keyword)
    _job(
        root,
        "detail-1",
        "detail",
        [_note(f"n{index}", comments or []) for index in range(1, 4)],
        note_ids=["n1", "n2", "n3"],
    )


def test_validator_accepts_complete_bound_run(tmp_path: Path) -> None:
    _valid_tree(tmp_path)
    assert probe.validate(tmp_path) == 0


@pytest.mark.parametrize(
    "representatives",
    [
        None,
        ["n1", "n2"],
        ["n1", "n2", "n3", "n4"],
        ["n1", None, "n3"],
        ["n1", "", "n3"],
        ["n1", " ", "n3"],
        ["n1", "n1", "n3"],
    ],
)
def test_validator_rejects_invalid_representative_id_triplets(
    tmp_path: Path, representatives: object, capsys: pytest.CaptureFixture[str]
) -> None:
    _valid_tree(tmp_path)
    detail_manifest = tmp_path / "detail-1" / "manifest.json"
    manifest = json.loads(detail_manifest.read_text(encoding="utf-8"))
    manifest["note_ids"] = representatives
    _write_json(detail_manifest, manifest)
    assert probe.validate(tmp_path) == 3
    assert "three non-empty distinct representative note IDs" in capsys.readouterr().out


def test_validator_rejects_four_detail_records_even_when_ids_deduplicate(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _valid_tree(tmp_path)
    notes = [_note("n1", []), _note("n2", []), _note("n3", []), _note("n3", [])]
    (tmp_path / "detail-1" / "notes.jsonl").write_text(
        "\n".join(json.dumps(note) for note in notes), encoding="utf-8"
    )
    assert probe.validate(tmp_path) == 3
    assert "exactly 3 Detail note records" in capsys.readouterr().out


@pytest.mark.parametrize(("count", "expected"), [(20, 0), (21, 3)])
def test_validator_enforces_first_level_comment_limit_on_otherwise_valid_artifacts(
    tmp_path: Path, count: int, expected: int
) -> None:
    comments = [
        {"comment_id": str(index), "content": "x", "is_sub_comment": False}
        for index in range(count)
    ]
    _valid_tree(tmp_path, comments)
    assert probe.validate(tmp_path) == expected


def test_validator_rejects_any_sub_comment(tmp_path: Path) -> None:
    _valid_tree(tmp_path, [{"comment_id": "c1", "content": "x", "is_sub_comment": True}])
    assert probe.validate(tmp_path) == 3


@pytest.mark.parametrize(("count", "expected"), [(20, 0), (21, 3)])
def test_validator_counts_real_separate_comment_records_per_note(
    tmp_path: Path,
    count: int,
    expected: int,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _valid_tree(tmp_path)
    comments = [_comment(f"c{index}", "n1") for index in range(count)]
    (tmp_path / "detail-1" / "detail_comments_20260903.jsonl").write_text(
        "\n".join(json.dumps(comment) for comment in comments), encoding="utf-8"
    )
    assert probe.validate(tmp_path) == expected
    output = capsys.readouterr().out
    if count == 21:
        assert "exceeds 20 first-level comments" in output


def test_validator_rejects_real_sub_comment_record_by_parent_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _valid_tree(tmp_path)
    comment = _comment("sub-1", "n1", parent_comment_id="parent-1")
    (tmp_path / "detail-1" / "detail_comments_20260903.jsonl").write_text(
        json.dumps(comment), encoding="utf-8"
    )
    assert probe.validate(tmp_path) == 3
    assert "second-level comments" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("mode", "detail", "manifest mode"),
        ("keyword", "wrong", "keyword"),
        ("started_at", "not-a-time", "started_at"),
        ("finished_at", "2020-01-01T00:00:00+00:00", "finished_at"),
        ("exit_code", 7, "exit_code"),
        ("raw_path", "elsewhere", "raw_path"),
        ("run_id", "foreign-run", "run_id"),
    ],
)
def test_validator_explicitly_rejects_each_tampered_search_manifest_field(
    tmp_path: Path,
    field: str,
    replacement: object,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _valid_tree(tmp_path)
    manifest_path = tmp_path / "search-1" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = replacement
    _write_json(manifest_path, manifest)
    assert probe.validate(tmp_path) == 3
    assert message in capsys.readouterr().out


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("mode", "search", "manifest mode"),
        ("started_at", "not-a-time", "started_at"),
        ("finished_at", "2020-01-01T00:00:00+00:00", "finished_at"),
        ("exit_code", 7, "exit_code"),
        ("raw_path", "elsewhere", "raw_path"),
        ("run_id", "foreign-run", "run_id"),
        ("note_ids", ["n1", "n2", "wrong"], "note IDs"),
    ],
)
def test_validator_explicitly_rejects_tampered_detail_manifest(
    tmp_path: Path,
    field: str,
    replacement: object,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _valid_tree(tmp_path)
    manifest_path = tmp_path / "detail-1" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest[field] = replacement
    _write_json(manifest_path, manifest)
    assert probe.validate(tmp_path) == 3
    assert message in capsys.readouterr().out


@pytest.mark.parametrize(
    ("field", "replacement", "message"),
    [
        ("run_id", "foreign-run-identifier-000000000000", "run_id"),
        ("started_at", "not-a-time", "started_at"),
        ("finished_at", "not-a-time", "finished_at"),
        ("status", "awaiting_detail", "status"),
    ],
)
def test_validator_rejects_each_tampered_top_level_run_field(
    tmp_path: Path,
    field: str,
    replacement: object,
    message: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _valid_tree(tmp_path)
    run_path = tmp_path / "run.json"
    run = json.loads(run_path.read_text(encoding="utf-8"))
    run[field] = replacement
    _write_json(run_path, run)
    assert probe.validate(tmp_path) == 3
    assert message in capsys.readouterr().out


def test_validator_rejects_job_finishing_after_top_level_run(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _valid_tree(tmp_path)
    manifest_path = tmp_path / "detail-1" / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["finished_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    _write_json(manifest_path, manifest)
    assert probe.validate(tmp_path) == 3
    assert "exceeds the top-level run" in capsys.readouterr().out


def _execution(raw_path: Path, *, exit_code: int = 0, stderr: str | None = None) -> CrawlExecution:
    started = datetime.now(UTC)
    return CrawlExecution(
        started, started + timedelta(seconds=1), exit_code, raw_path.resolve(), stderr
    )


class _FakeAdapter:
    def __init__(self, settings: MediaCrawlerSettings) -> None:
        self.settings = settings

    async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution:
        raw_path.mkdir(parents=True, exist_ok=True)
        (raw_path / "notes.jsonl").write_text(
            json.dumps(_note(f"n{KEYWORDS.index(keyword) + 1}")), encoding="utf-8"
        )
        return _execution(raw_path)

    async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution:
        raw_path.mkdir(parents=True, exist_ok=True)
        resolved_ids = [urlparse(note_url).path.rstrip("/").split("/")[-1] for note_url in note_ids]
        (raw_path / "notes.jsonl").write_text(
            "\n".join(json.dumps(_note(note_id, [])) for note_id in resolved_ids),
            encoding="utf-8",
        )
        return _execution(raw_path)


def _live_dependencies(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = MediaCrawlerSettings(checkout_path=tmp_path / "checkout")
    monkeypatch.setattr(MediaCrawlerSettings, "from_yaml", classmethod(lambda cls, path: settings))
    monkeypatch.setattr(MediaCrawlerSettings, "verify_checkout", lambda self: None)
    monkeypatch.setattr(probe, "MediaCrawlerAdapter", _FakeAdapter)


@pytest.mark.asyncio
async def test_live_probe_binds_search_and_detail_to_same_unpredictable_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    assert await probe.run_live(root, [], None) == 2
    run_manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
    run_id = run_manifest["run_id"]
    assert isinstance(run_id, str) and len(run_id) >= 32 and run_id != RUN_ID
    assert run_manifest["status"] == "awaiting_detail"
    assert run_manifest["finished_at"] is None
    for path in root.glob("search-*"):
        assert json.loads((path / "manifest.json").read_text(encoding="utf-8"))["run_id"] == run_id
    assert f"--run-id {run_id}" in capsys.readouterr().out
    assert await probe.run_live(root, ["n1", "n2", "n3"], run_id) == 0
    completed = json.loads((root / "run.json").read_text(encoding="utf-8"))
    assert completed["status"] == "completed"
    assert completed["finished_at"]
    assert (
        json.loads((root / "detail-1" / "manifest.json").read_text(encoding="utf-8"))["run_id"]
        == run_id
    )
    assert probe.validate(root) == 0


@pytest.mark.asyncio
async def test_live_probe_resolves_selected_ids_to_tokenized_search_urls_for_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CapturingAdapter(_FakeAdapter):
        detail_targets: list[str] = []

        async def run_detail(
            self, note_ids: list[str], raw_path: Path
        ) -> CrawlExecution:
            type(self).detail_targets = note_ids
            raw_path.mkdir(parents=True, exist_ok=True)
            return _execution(raw_path, exit_code=7)

    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    monkeypatch.setattr(probe, "MediaCrawlerAdapter", CapturingAdapter)
    assert await probe.run_live(root, [], None) == 2
    run_id = json.loads((root / "run.json").read_text(encoding="utf-8"))["run_id"]
    selected_ids: list[str] = []
    expected_urls: list[str] = []
    for index, search_path in enumerate(sorted(root.glob("search-*")), 1):
        record_path = search_path / "notes.jsonl"
        record = json.loads(record_path.read_text(encoding="utf-8"))
        note_id = str(record["note_id"])
        note_url = (
            f"https://www.xiaohongshu.com/explore/{note_id}"
            f"?xsec_token=token-{index}&xsec_source=pc_search"
        )
        record["note_url"] = note_url
        record_path.write_text(json.dumps(record), encoding="utf-8")
        selected_ids.append(note_id)
        expected_urls.append(note_url)

    assert await probe.run_live(root, selected_ids, run_id) == 7
    assert CapturingAdapter.detail_targets == expected_urls


@pytest.mark.asyncio
@pytest.mark.parametrize("run_id", [None, "wrong-run"])
async def test_live_probe_rejects_absent_or_wrong_resume_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, run_id: str | None
) -> None:
    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    assert await probe.run_live(root, [], None) == 2
    assert await probe.run_live(root, ["n1", "n2", "n3"], run_id) == 3
    assert not (root / "detail-1").exists()


@pytest.mark.asyncio
async def test_live_probe_rejects_expired_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    assert await probe.run_live(root, [], None) == 2
    run_path = root / "run.json"
    run_manifest = json.loads(run_path.read_text(encoding="utf-8"))
    run_manifest["started_at"] = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    _write_json(run_path, run_manifest)
    assert await probe.run_live(root, ["n1", "n2", "n3"], run_manifest["run_id"]) == 3


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["foreign", "time", "detail"])
async def test_live_probe_rejects_foreign_mixed_time_inconsistent_or_existing_detail(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    assert await probe.run_live(root, [], None) == 2
    run_manifest = json.loads((root / "run.json").read_text(encoding="utf-8"))
    run_id = run_manifest["run_id"]
    if mutation == "detail":
        (root / "detail-1").mkdir()
    else:
        path = next(root.glob("search-1-*")) / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["run_id" if mutation == "foreign" else "started_at"] = (
            "foreign-run" if mutation == "foreign" else "2020-01-01T00:00:00+00:00"
        )
        _write_json(path, manifest)
    assert await probe.run_live(root, ["n1", "n2", "n3"], run_id) == 3


@pytest.mark.asyncio
async def test_live_probe_will_not_reuse_three_historical_search_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "raw"
    root.mkdir()
    _live_dependencies(monkeypatch, tmp_path)
    for index, keyword in enumerate(KEYWORDS, 1):
        _job(root, f"search-{index}", "search", [_note(f"s{index}")], keyword=keyword)
    assert await probe.run_live(root, ["n1", "n2", "n3"], RUN_ID) == 3


@pytest.mark.asyncio
async def test_live_probe_output_never_leaks_redacted_adapter_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    class FailingAdapter(_FakeAdapter):
        async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution:
            raw_path.mkdir(parents=True, exist_ok=True)
            return _execution(
                raw_path,
                exit_code=7,
                stderr="Cookie: sid=probe-first; web_session=probe-tail",
            )

    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    monkeypatch.setattr(probe, "MediaCrawlerAdapter", FailingAdapter)
    assert await probe.run_live(root, [], None) == 7
    output = capsys.readouterr().out
    assert "probe-first" not in output
    assert "probe-tail" not in output
    assert "[REDACTED]" in output


@pytest.mark.asyncio
async def test_live_probe_marks_cancelled_search_run_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CancelledAdapter(_FakeAdapter):
        async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution:
            raw_path.mkdir(parents=True, exist_ok=True)
            raise asyncio.CancelledError

    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    monkeypatch.setattr(probe, "MediaCrawlerAdapter", CancelledAdapter)
    with pytest.raises(asyncio.CancelledError):
        await probe.run_live(root, [], None)
    run = json.loads((root / "run.json").read_text(encoding="utf-8"))
    assert run["status"] == "interrupted"
    assert run["finished_at"]


@pytest.mark.asyncio
async def test_live_probe_marks_cancelled_detail_run_interrupted_and_unresumable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class CancelledDetailAdapter(_FakeAdapter):
        async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution:
            raw_path.mkdir(parents=True, exist_ok=True)
            (raw_path / "partial.jsonl").write_text("partial", encoding="utf-8")
            raise asyncio.CancelledError

    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    assert await probe.run_live(root, [], None) == 2
    run_id = json.loads((root / "run.json").read_text(encoding="utf-8"))["run_id"]
    monkeypatch.setattr(probe, "MediaCrawlerAdapter", CancelledDetailAdapter)

    with pytest.raises(asyncio.CancelledError):
        await probe.run_live(root, ["n1", "n2", "n3"], run_id)

    run = json.loads((root / "run.json").read_text(encoding="utf-8"))
    assert run["status"] == "interrupted"
    assert run["finished_at"]
    assert (root / "detail-1" / "partial.jsonl").exists()
    assert not (root / "detail-1" / "manifest.json").exists()
    assert await probe.run_live(root, ["n1", "n2", "n3"], run_id) == 3


@pytest.mark.asyncio
async def test_live_probe_marks_detail_exception_failed_and_unresumable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class FailingDetailAdapter(_FakeAdapter):
        async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution:
            raw_path.mkdir(parents=True, exist_ok=True)
            (raw_path / "partial.jsonl").write_text("partial", encoding="utf-8")
            raise RuntimeError("detail crashed")

    root = tmp_path / "raw"
    _live_dependencies(monkeypatch, tmp_path)
    assert await probe.run_live(root, [], None) == 2
    run_id = json.loads((root / "run.json").read_text(encoding="utf-8"))["run_id"]
    monkeypatch.setattr(probe, "MediaCrawlerAdapter", FailingDetailAdapter)

    with pytest.raises(RuntimeError, match="detail crashed"):
        await probe.run_live(root, ["n1", "n2", "n3"], run_id)

    run = json.loads((root / "run.json").read_text(encoding="utf-8"))
    assert run["status"] == "failed"
    assert run["finished_at"]
    assert (root / "detail-1" / "partial.jsonl").exists()
    assert not (root / "detail-1" / "manifest.json").exists()
    assert await probe.run_live(root, ["n1", "n2", "n3"], run_id) == 3


def test_cli_passes_explicit_run_id_for_detail_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: dict[str, object] = {}

    async def fake_run_live(root: Path, note_ids: list[str], run_id: str | None) -> int:
        captured.update(root=root, note_ids=note_ids, run_id=run_id)
        return 0

    monkeypatch.setattr(probe, "run_live", fake_run_live)
    monkeypatch.setattr(
        "sys.argv", ["probe", "--run-id", RUN_ID, "--detail-note", "n1", str(tmp_path)]
    )
    assert probe.main() == 0
    assert captured == {"root": tmp_path, "note_ids": ["n1"], "run_id": RUN_ID}
