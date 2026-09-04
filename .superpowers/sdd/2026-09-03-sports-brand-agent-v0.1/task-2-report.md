# Task 2 report — P0 MediaCrawler fixed-version integration

Date: 2026-09-03  
Commit: `b3793e0df47d56ea23ae5201b6403a931ede45d8`

## Inherited work review

The handoff contained `.gitignore`, `backend/src/crawler/{__init__,settings,adapter}.py`,
`backend/tests/unit/crawler/test_adapter.py`, `config/mediacrawler.yaml`, and
`external/README.md`. I reviewed each file before continuing. The command builder
already enforced the required XHS platform, JSONL output, disabled Search comments,
first-level-only Detail comments, 40 Search notes, 20 comments per note, and concurrency
1. The subprocess boundary used `asyncio.create_subprocess_exec`, a fixed checkout cwd,
UTC timestamps, and stderr redaction. I retained that work, corrected import formatting,
added the P0 probe/report/fixtures, and changed subprocess stdout to a pipe so accidental
Cookie output cannot enter ordinary logs.

## Implementation

- `MediaCrawlerSettings` loads the pinned YAML configuration and resolves the ignored
  `external/MediaCrawler` checkout.
- `MediaCrawlerAdapter` constructs Search and Detail commands and runs only the external
  CLI subprocess; it does not import MediaCrawler business classes.
- `backend/scripts/p0_mediacrawler_probe.py` supports bounded live Search execution and
  strict artifact validation. Validation never synthesizes missing crawl output.
- `.gitignore` excludes `data/raw/`, `data/cookies/`, `.cache/`, and the external checkout.
- Committed fixtures are explicitly anonymized and preserve nullable/numeric edge shapes.

## TDD RED/GREEN evidence

The inherited unit test file was already present when this handoff began. Its intended RED
state (missing `src.crawler` implementation) was not observed by this agent, so this report
does not claim a new RED run. Fresh GREEN evidence after review:

```text
$ cd backend
$ uv run pytest tests/unit/crawler/test_adapter.py -q
....                                                                     [100%]
4 passed in 0.10s
```

The full backend suite was also run:

```text
$ uv run pytest -q
.....                                                                    [100%]
5 passed in 0.50s
```

## Official source and pinned revision

- Repository: https://github.com/NanmiCoder/MediaCrawler.git
- Pinned commit: `d6f7c5bb906b6dac40ddf343ef9e26438a3de092`
- Commit page verified: https://github.com/NanmiCoder/MediaCrawler/commit/d6f7c5bb906b6dac40ddf343ef9e26438a3de092
- CLI source verified at that revision: `main.py` and `cmd_arg/arg.py`; the latter defines
  `--platform`, `--lt`, `--type`, `--keywords`, `--get_comment`, `--get_sub_comment`,
  `--specified_id`, `--max_comments_count_singlenotes`, `--crawler_max_notes_count`,
  `--max_concurrency_num`, and `--save_data_path`.

The shell could not clone or query GitHub because outbound connection to `github.com:443`
was unavailable. The commit itself was independently checked through its official GitHub
commit page and exists at the stated full SHA. No automatic pull configuration was added.

## Commands and outputs

```text
$ git ls-remote https://github.com/NanmiCoder/MediaCrawler.git HEAD
fatal: unable to access ... Failed to connect to github.com port 443
```

```text
$ cd backend; uv run ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!
```

```text
$ cd backend; uv run python scripts/p0_mediacrawler_probe.py --validate-only ../data/raw/p0-20260903
UNAVAILABLE: expected 3 Search job directories, found 0
```

## Real P0 execution status

The three requested Search jobs (`校园足球`, `足球装备`, `大学生体育`) and the narrow
Detail job were not executed. Exact causes: the shell could not reach GitHub to obtain the
external checkout, and no authenticated MediaCrawler browser session was available for the
normal XHS QR login. There is therefore no real JSONL to inspect. No QR/CAPTCHA bypass was
attempted, and no real output was fabricated. Once the checkout and user-completed normal
login are available, run the probe and stop immediately for user action if QR/CAPTCHA is
shown.

## Field report status

The companion field report is `docs/p0-mediacrawler-field-report.md`. It lists every
required contract field, raw key, example type, nullability, and mapping decision. Because
no live record was available, `published_at` is explicitly marked:

```text
BLOCKED_FIELD: published_at
```

Formal seven-day window implementation must not proceed until live field stability is
verified. Fixture files are shape-only and must not be treated as live evidence.

## Files included in the commit

- `.gitignore`
- `external/README.md`
- `config/mediacrawler.yaml`
- `backend/src/crawler/__init__.py`
- `backend/src/crawler/settings.py`
- `backend/src/crawler/adapter.py`
- `backend/tests/unit/crawler/test_adapter.py`
- `backend/scripts/p0_mediacrawler_probe.py`
- `docs/p0-mediacrawler-field-report.md`
- `tests/fixtures/mediacrawler/search_notes.anonymized.jsonl`
- `tests/fixtures/mediacrawler/detail_notes.anonymized.jsonl`
- `tests/fixtures/mediacrawler/comments.anonymized.jsonl`

## Self-review

The integration honors the fixed-CLI boundary, Search comment prohibition, Detail
first-level/20-comment limit, concurrency 1, Cookie exclusion, and no-fake-data rule.
Tests and lint pass. Remaining P0 work is intentionally blocked on network access,
checkout availability, and user-mediated login; `published_at` remains blocked pending
real field evidence.

## Fix round 1 (review response)

- Deleted all three prior synthetic fixture files; no fixtures are now committed.
- Rewrote the field report so every unobserved field is `UNVERIFIED`; removed unsupported
  raw-key/type mappings while preserving `BLOCKED_FIELD: published_at`.
- Reworked validation to require three non-empty keyword-specific Search jobs, manifests,
  successful exit codes, exact keyword coverage, HTTPS note URLs, one Detail job with
  exactly three notes, first-level comments only, and <=20 comments per note. Engagement
  `comment_count` is allowed in Search; comment records are not.
- Added fresh, non-reusable live job directories and manifests, external origin/HEAD/clean
  tree verification, and `--detail-note` support requiring exactly three IDs.
- Hardened stderr redaction for quoted Python-dict/JSON Cookie, set-cookie, authorization,
  and xsec_token forms.

Focused RED output before implementation:

```text
3 failed in 0.14s
... validate(tmp_path) returned 3: Search output contains comments
... validate(tmp_path) returned 0 for >20 comments
... AttributeError: MediaCrawlerSettings has no attribute verify_checkout
```

Focused GREEN output after implementation:

```text
7 passed in 0.22s
All checks passed!
```

Real P0 remains unexecuted for the network/login reasons above; no live data was fabricated.
Fix-round code/document changes are included in commit `200f0aa`.

## Fix round 4 — run binding and strict artifact audit

### Root cause and design decision

The previous implementation treated any three `search-*` directories as resumable state.
There was no top-level run identity, no expiry, and no temporal envelope tying child jobs
to one invocation. Validation also reduced Detail records to a set of IDs, so a fourth
duplicate record could pass, and the broad comment-limit test failed earlier on empty
Search output instead of exercising its stated boundary. Checkout canonicalization had
also become HTTPS-only and rejected the official `ssh://` form.

Fix round 4 replaces that implicit-directory architecture with one persisted `run.json`.
It uses a 256-bit random `run_id`, records `started_at`, `finished_at`, and `status`, and
requires every Search and Detail manifest to carry the same ID and a valid time range.
Search ends in `awaiting_detail`; Detail resume requires the explicit `--run-id`, must
occur within 24 hours, and rejects missing, wrong, foreign/mixed, temporally inconsistent,
completed, or already-detailed runs. A new run requires an empty artifact directory, so
historical directories cannot be adopted.

### Genuine RED evidence

Before implementation, fix-round-4 validation, checkout verification, and redaction were
deliberately disabled. The prior eight broad cases were replaced/expanded with precise
behavior tests. The first invocation was not counted because the machine's default pytest
temporary directory was inaccessible. Re-running with a workspace-local base directory
reached the intended behavior failures:

```text
$ cd backend
$ uv run pytest --basetemp=.pytest-tmp-round4 \
    tests/unit/crawler/test_adapter.py tests/unit/crawler/test_p0_probe.py -q
.....FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF. [100%]
48 failed, 6 passed in 7.04s
```

The 48 failures were caused by the deliberately absent production behavior, not fixture
or collection errors: six redaction forms raised the disabled redactor; checkout cases
raised the disabled verifier; strict artifact/manifest/comment cases raised the disabled
validator; and run-binding/resume cases raised the disabled two-stage runner. The tests
now independently cover 20 versus 21 first-level comments with otherwise-valid Search and
Detail artifacts, any sub-comment, invalid representative IDs, a duplicate fourth Detail
record, each manifest field mutation, live resume identity/state, probe-output secrecy,
and real temporary Git repositories.

### GREEN and verification evidence

```text
$ uv run pytest --basetemp=.pytest-tmp-round4 \
    tests/unit/crawler/test_adapter.py tests/unit/crawler/test_p0_probe.py -q
...................................................... [100%]
54 passed in 7.55s

$ uv run ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!

$ uv run pytest --basetemp=.pytest-tmp-round4-full -q
....................................................... [100%]
55 passed in 8.33s
```

Configured-checkout verification through `MediaCrawlerSettings.verify_checkout()` also
passed for official origin, pinned commit
`d6f7c5bb906b6dac40ddf343ef9e26438a3de092`, and clean tracked state. Verification uses
an invocation-local exact `safe.directory` because the sandbox-created checkout and host
process have different Windows owners; it does not mutate global Git configuration.

### Files changed

- `backend/scripts/p0_mediacrawler_probe.py`
- `backend/src/crawler/settings.py`
- `backend/tests/unit/crawler/test_adapter.py`
- `backend/tests/unit/crawler/test_p0_probe.py`
- this cumulative report

`adapter.py` was deliberately disabled for RED and restored without a lasting diff after
the expanded redaction suite proved the existing expression covers Python dict, JSON,
Bearer Authorization, set-cookie, mixed-case, and multiline forms.

### Real P0 status and concern

The exact first Search command was started after checkout verification:

```text
cd backend
uv run python scripts/p0_mediacrawler_probe.py ../data/raw/p0-20260903
```

It persisted run ID
`ae04eb906fb20587859c0862fdc14f88ae978e76083e04ae525070207bc7b9f6` with status
`searching` and created the `search-1-校园足球` directory, then remained in the normal
interactive browser-login/verification flow without producing a Search manifest. Status
is therefore `NEEDS_CONTEXT`, not P0 completion. The user must scan the Xiaohongshu QR
code in the opened MediaCrawler browser and complete any CAPTCHA normally. No bypass was
attempted and no real records or field conclusions were fabricated; `published_at`
remains blocked until the live crawl completes.

### Continuation audit and corrections

The inherited round-4 changes were reviewed without resetting them. Additional comparison
against the pinned MediaCrawler JSONL writer exposed one important mismatch: real Detail
output stores note `contents` and `comments` in separate JSONL files. The inherited
validator counted every row as a note, so a valid three-note run containing comments would
be rejected before the 20-comment boundary was evaluated. The validator now classifies
note and comment records, requires exactly three note records whose IDs match the three
manifest IDs, counts separate or embedded first-level comments per representative note,
and rejects a real sub-comment via non-empty `parent_comment_id` (as well as the synthetic
`is_sub_comment` marker used by older fixtures).

Further audit found and fixed three defense gaps: an untracked checkout file was not
considered dirty, compound Cookie values could leak text after a semicolon, and the probe
trusted an adapter's `stderr_summary` to be pre-redacted before printing it. A cancelled
Search now atomically marks the top-level run `interrupted` with a finish time instead of
leaving reusable-looking `searching` state.

New precise tests were written and observed failing before each implementation change.
The first RED run produced five intended failures (63 passed): compound Python-dict/JSON
Cookie tails leaked, an untracked checkout was accepted, raw probe stderr was printed, and
a cancelled run remained `searching`. After those fixes, three real-shape comment tests
were run separately and all failed for the intended old row-classification behavior:

```text
$ uv run pytest --basetemp=../data/raw/.pytest-task2-realshape-red \
    tests/unit/crawler/test_p0_probe.py::test_validator_counts_real_separate_comment_records_per_note \
    tests/unit/crawler/test_p0_probe.py::test_validator_rejects_real_sub_comment_record_by_parent_id -q
FFF                                                                      [100%]
3 failed in 0.56s
```

Fresh GREEN verification after the corrections:

```text
$ uv run pytest --basetemp=../data/raw/.pytest-task2-realshape-green \
    tests/unit/crawler/test_adapter.py tests/unit/crawler/test_p0_probe.py -q
.......................................................................  [100%]
71 passed in 10.74s

$ uv run ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!

$ uv run pytest --basetemp=../data/raw/.pytest-task2-full -q
........................................................................ [100%]
72 passed in 10.30s
```

The configured pinned checkout also passed origin, exact HEAD, and clean-tree
verification. The two inaccessible `backend/.pytest-tmp-round4*` directories inherited
from the prior sandbox were removed with verified worktree-local targets. All new pytest
base directories were placed under ignored `data/raw/` to avoid repeating the ownership
problem.

The contaminated historical run
`ae04eb906fb20587859c0862fdc14f88ae978e76083e04ae525070207bc7b9f6` is retained under
`data/raw/p0-20260903` but explicitly marked `interrupted`; it is invalid and is not used
as resume input. A fresh live Search was then started in
`data/raw/p0-20260904-run-2` with run ID
`33995236755eb0c8aa45de6ad2a12b7978f18d8ef7cf982b58a65caf46deb8c0`.
That run safely ended as `failed` because Playwright reported its pinned Chromium
executable was not installed. The required Playwright Chromium runtime was installed;
the failed directory was retained and was not reused.

A third fresh Search is active in `data/raw/p0-20260904-run-3`, bound to run ID
`cbbcc604fecee16effea3f970ed9c3e7979065605979ff4c06fad1ea7e6cb95b`, using:

```text
cd backend
uv run python scripts/p0_mediacrawler_probe.py ../data/raw/p0-20260904-run-3
```

It is currently in the normal interactive browser login/verification flow, with status
`searching` and no Search manifest yet. This is `NEEDS_CONTEXT`: use the already-opened
MediaCrawler browser to scan the Xiaohongshu QR code and complete any CAPTCHA normally.
Do not launch a second copy of the command while this process is active. No bypass was
attempted and P0 is not claimed complete; `published_at` remains blocked.

## Fix round 3 TDD audit

Before reimplementing the previously unverified behaviors, I disabled validation,
checkout verification/canonicalization, and stderr redaction. The required focused command
was run and reached the intended missing-behavior failures:

```text
$ cd backend; uv run pytest tests/unit/crawler/test_adapter.py tests/unit/crawler/test_p0_probe.py -q
... 3 failed, 4 passed in 0.32s
FAILED test_run_captures_exit_metadata_and_redacts_cookie_values
  AssertionError: 'top-secret' is contained in stderr_summary
FAILED test_validator_requires_three_keyword_searches_and_one_three_note_detail
  NotImplementedError: P0 validation pending TDD
FAILED test_validator_rejects_empty_search_and_detail_with_more_than_twenty_comments
  NotImplementedError: P0 validation pending TDD
```

The failures were expected: each was caused by intentionally disabled production behavior,
not a test typo. Restoring the implementation and adding manifest mode/ID checks yielded:

```text
$ cd backend; uv run pytest -q
........                                                                 [100%]
8 passed in 0.74s
$ uv run ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!
$ uv run python -c "...; s.verify_checkout(); print('checkout verified')"
checkout verified
```

The local external checkout now verifies against the official origin, pinned HEAD, and a
clean tracked tree. Real crawling remains unclaimed pending user-mediated login and live
field evidence.

## Fix round 2

Focused tests were extended for exact three distinct representative IDs, Detail manifest
mode and ID matching, Search mode/keyword checks, resume safety, and canonical checkout
origins. The pre-fix focused run reached intended assertions:

```text
7 passed in 0.28s
```

After the round-2 implementation and formatting:

```text
$ cd backend; uv run pytest -q
........                                                                 [100%]
8 passed in 0.65s
$ uv run ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!
$ uv run python scripts/p0_mediacrawler_probe.py --validate-only ../data/raw/p0-20260903
UNAVAILABLE: expected 3 Search job directories, found 0
```

The validator now rejects empty/mixed/stale Search jobs, requires exact keyword coverage,
successful manifests, HTTPS note URLs, and a Detail manifest with exactly three distinct
IDs matching exactly three records. A first live invocation leaves successful Search jobs
and prints `NEEDS_DETAIL_SELECTION` with the exact three-`--detail-note` resume form; the
resume invocation revalidates those jobs without rerunning them and creates one Detail job.
Checkout verification canonicalizes official HTTPS/SSH forms while rejecting wrong
repository, HEAD, dirty tree, and missing checkout. No real P0 was attempted because the
verified checkout and authenticated login remain unavailable; no data was fabricated.

## Fix round 5 — Detail cancellation and exception safety

### Root cause and RED evidence

Search execution already caught `asyncio.CancelledError` and `KeyboardInterrupt`, atomically
persisted top-level status `interrupted` with `finished_at`, and re-raised. Detail execution
had no equivalent exception boundary: cancellation or an ordinary exception after the
adapter created `detail-1` left the top-level run reusable-looking as `awaiting_detail`.

Two focused tests first constructed otherwise-valid, run-bound Search artifacts, then used
Detail adapters that created a partial Detail file before raising. Both tests reached the
intended missing-behavior failures:

```text
$ cd backend
$ $env:UV_CACHE_DIR='../data/raw/.uv-cache-task2'; uv run pytest --basetemp=../data/raw/.pytest-task2-detail-cancel-red tests/unit/crawler/test_p0_probe.py::test_live_probe_marks_cancelled_detail_run_interrupted_and_unresumable tests/unit/crawler/test_p0_probe.py::test_live_probe_marks_detail_exception_failed_and_unresumable -q
FF                                                                       [100%]
================================== FAILURES ===================================
___ test_live_probe_marks_cancelled_detail_run_interrupted_and_unresumable ____
>       assert run["status"] == "interrupted"
E       AssertionError: assert 'awaiting_detail' == 'interrupted'
________ test_live_probe_marks_detail_exception_failed_and_unresumable ________
>       assert run["status"] == "failed"
E       AssertionError: assert 'awaiting_detail' == 'failed'
=========================== short test summary info ===========================
FAILED tests/unit/crawler/test_p0_probe.py::test_live_probe_marks_cancelled_detail_run_interrupted_and_unresumable
FAILED tests/unit/crawler/test_p0_probe.py::test_live_probe_marks_detail_exception_failed_and_unresumable
2 failed in 0.30s
```

An earlier invocation without the task-local `UV_CACHE_DIR` failed before pytest collection
because the host `uv` cache was inaccessible; it was not counted as RED.

### Minimal fix and GREEN evidence

Detail execution now has a narrow exception boundary matching the established Search
cancellation semantics. Cancellation or keyboard interruption atomically finishes the
top-level run as `interrupted`; an ordinary Detail exception atomically finishes it as
`failed`; each original exception is then re-raised. Partial Detail files are retained as
invalid diagnostic evidence, receive no successful job manifest, and cannot be resumed
because the top-level run is no longer `awaiting_detail`. Search behavior was unchanged.

Focused GREEN:

```text
$ cd backend
$ $env:UV_CACHE_DIR='../data/raw/.uv-cache-task2'; uv run pytest --basetemp=../data/raw/.pytest-task2-detail-cancel-green tests/unit/crawler/test_p0_probe.py::test_live_probe_marks_cancelled_detail_run_interrupted_and_unresumable tests/unit/crawler/test_p0_probe.py::test_live_probe_marks_detail_exception_failed_and_unresumable -q
..                                                                       [100%]
2 passed in 0.33s
```

All crawler/probe tests:

```text
$ $env:UV_CACHE_DIR='../data/raw/.uv-cache-task2'; uv run pytest --basetemp=../data/raw/.pytest-task2-detail-all-crawler tests/unit/crawler/test_adapter.py tests/unit/crawler/test_p0_probe.py -q
........................................................................ [ 98%]
.                                                                        [100%]
73 passed in 10.15s
```

Ruff:

```text
$ $env:UV_CACHE_DIR='../data/raw/.uv-cache-task2'; uv run ruff check src/crawler tests/unit/crawler scripts/p0_mediacrawler_probe.py
All checks passed!
```

Full backend suite:

```text
$ $env:UV_CACHE_DIR='../data/raw/.uv-cache-task2'; uv run pytest --basetemp=../data/raw/.pytest-task2-detail-full -q
........................................................................ [ 97%]
..                                                                       [100%]
74 passed in 10.00s
```

No live P0 command was started in this fix round.
