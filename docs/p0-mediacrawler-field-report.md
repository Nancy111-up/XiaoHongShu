# MediaCrawler P0 field report (2026-09-04)

Repository: https://github.com/NanmiCoder/MediaCrawler.git  
Pinned revision: `d6f7c5bb906b6dac40ddf343ef9e26438a3de092`  
Status: **Search live-verified; Detail and comment fields blocked.** Run
`cbbcc604fecee16effea3f970ed9c3e7979065605979ff4c06fad1ea7e6cb95b`
(`data/raw/p0-20260904-run-3`) completed three serial Search jobs with exit code 0 and
`--get_comment false --get_sub_comment false`: `校园足球` = 40 JSONL rows,
`足球装备` = 40, and `大学生体育` = 40. Search yielded no comment records. The 120 real
records contain one cross-keyword duplicate note ID. No mapping below is inferred from a
fixture or demo record.

## Field verification

`Nullable` reports only the observed 120-record Search sample, not a general API contract.
`UNVERIFIED` requires completed live Detail JSONL.

| Contract field | Exact raw key | Example type | Nullable | Decision |
|---|---|---|---|---|
| `note_id` | `note_id` | string | no empty/null | retain as source note identifier |
| `title` | `title` | string | no empty/null | map directly |
| `body` | `desc` | string | 3 empty strings; no null | map directly; preserve empty string |
| `author_id` | `creator_hash` | string | no empty/null | map directly; platform pseudonymous identifier |
| `author_name` | `nickname` | string | no empty/null | map directly; anonymize in any committed fixture |
| `published_at` | `time` | integer (milliseconds-like) | no empty/null | **BLOCKED_FIELD: published_at** — epoch/unit/semantic stability across Detail and runs is unverified |
| `likes` | `liked_count` | string | no empty/null | retain raw string; compact Chinese units occur, so no numeric coercion is evidenced |
| `collects` | `collected_count` | string | no empty/null | retain raw string; no numeric coercion is evidenced |
| `comments` | `comment_count` | string | 4 empty strings; no null | Search engagement count only; preserve raw string/empty shape |
| `url` | `note_url` | string | no empty/null | map directly for live validation; token-bearing query must not enter fixtures/report examples |
| `comment_id` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `comment_content` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

Search engagement `comment_count`, if present in a real note record, is a count and is not
comment content. The validator permits it while rejecting comment record files or embedded
comment records in Search output. Detail must contain only first-level comments, at most 20
per note, for exactly three representative notes.

## Blockers and safety

Three distinct, relevant and relatively high-engagement representative notes were selected
from the real Search output, one per keyword. Their real IDs remain only in ignored raw
manifests/commands; completed fixtures/report would use aliases. The same run's Detail
attempt was started with first-level-only comments and the 20-comment limit, but failed
before crawl output: the configured runner inherited an invalid checkout virtual
environment whose interpreter path no longer existed, then could not read uv's managed
Python directory. The run was correctly marked `failed` and is not reused.

An isolated ignored Python 3.11 environment was built from the pinned lockfile. A new run
`ecc7db9e318c507ba8d6cbf37a3eb082e8ec1dd80d760e47a5470b06aae50c82` then exited without
a Search manifest or diagnostic output; it is explicitly marked `interrupted` and is not
evidence. Strict validation cannot pass and no Detail/comment fixtures are created: doing
so would fabricate evidence. Formal seven-day implementation remains blocked at
`BLOCKED_FIELD: published_at` until real Detail output verifies timestamp semantics and
stability. QR/CAPTCHA was not bypassed; cookies remain outside Git, business DB, frontend,
and ordinary logs.

## Execution and verification record

Actual Search invocation (from `backend`):

```text
uv run python scripts/p0_mediacrawler_probe.py ../data/raw/p0-20260904-run-3
```

The three selected IDs were passed to the Detail resume with the run ID above. To avoid
putting live note identifiers in a committed artifact, they are recorded here as
`CAMPUS_FOOTBALL_NOTE_A`, `FOOTBALL_GEAR_NOTE_B`, and `UNIVERSITY_SPORT_NOTE_C`.
They are distinct authors and originate respectively from `校园足球`, `足球装备`, and
`大学生体育`. Detail manifest exit code was 2; produced note records = 0 and produced
first-level comment records = 0. Thus the required maximum of 20 comments per note was
requested but not live-observed.

Strict validation was actually run:

```text
python scripts/p0_mediacrawler_probe.py --validate-only ../data/raw/p0-20260904-run-3
INVALID: top-level run status must be completed
```

This is the expected honest result for a failed Detail job, not a passing claim. Fresh
verification of the unchanged crawler/probe code was:

```text
python -m pytest --basetemp=../data/raw/.pytest-task2-live-crawler tests/unit/crawler/test_adapter.py tests/unit/crawler/test_p0_probe.py -q
73 passed in 9.35s

ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!

python -m pytest --basetemp=../data/raw/.pytest-task2-live-full -q
74 passed in 9.14s
```
