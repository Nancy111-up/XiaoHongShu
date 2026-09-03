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
