# MediaCrawler P0 field report (2026-09-06)

Repository: https://github.com/NanmiCoder/MediaCrawler.git  
Pinned revision: `d6f7c5bb906b6dac40ddf343ef9e26438a3de092`  
Status: **PASS. Search, Detail, first-level comments, and mandatory field mappings are live-verified.**

The validated run is `de3400f00fe4cb2e7ed4bb964dcfd79f6125d7a6a54244bdc2546d34bb333794`
under ignored raw path `data/raw/p0-20260906-run-7`. It contains three serial Search
jobs with comments disabled (`校园足球`, `足球装备`, `大学生体育`, 40 records each),
followed by one Detail job for exactly three distinct representative notes from distinct
authors. Detail produced three note records and 60 first-level comment records, exactly 20
per representative note, with no sub-comments.

No real note ID, author identifier/name, title, body, comment text, token-bearing URL,
Cookie, or token is committed. The checked-in fixtures are structurally derived and fully
anonymized.

## Field verification

`Nullable` describes this 2026-09-06 live sample. Raw engagement fields remain strings
because compact Chinese units and empty strings occur. Normalization must preserve missing
values rather than silently turning them into zero.

| Contract field | Exact raw key | Observed type | Nullable / empty | Mapping decision |
|---|---|---|---|---|
| `note_id` | `note_id` | string | 0/120 Search and 0/3 Detail empty/null | map directly as source identifier |
| `title` | `title` | string | 0/120 Search and 0/3 Detail empty/null | map directly |
| `body` | `desc` | string | 3/120 Search empty; 0 null | map directly and preserve empty string |
| `author_id` | `creator_hash` | string | no empty/null in Search or Detail | map directly; anonymize in fixtures |
| `author_name` | `nickname` | string | no empty/null in Search or Detail | map directly; anonymize in fixtures |
| `published_at` | `time` | integer (`Int64`) | no empty/null | interpret as Unix epoch milliseconds; all Detail values are 13 digits, convert to plausible non-future 2025–2026 UTC instants, and match the corresponding Search value for 3/3 representatives |
| `likes` | `liked_count` | string | no empty/null in this sample | retain raw string; parse compact units only in a separate normalizer |
| `collects` | `collected_count` | string | no empty/null in this sample | retain raw string; parse compact units only in a separate normalizer |
| `comments` | `comment_count` | string | 6/120 Search empty; 0 null | engagement count only, not comment content; retain raw value |
| `url` | `note_url` | string | no empty/null | map canonical note URL; strip `xsec_token` and other query parameters before persistence outside the ignored raw boundary |
| `comment_id` | `comment_id` | string | 0/60 empty/null | map directly as source comment identifier |
| `comment_content` | `content` | string | 2/60 empty; 0 null | map directly and preserve empty string |

Live comment records also expose `note_id`, `create_time`, `creator_hash`, `nickname`,
`sub_comment_count`, `pictures`, `parent_comment_id`, `last_modify_ts`, and `like_count`.
All 60 observed `parent_comment_id` values are empty, confirming first-level-only output.

## Root-cause findings

Two distinct causes explained the earlier failed Detail attempt:

1. The restricted development subprocess could not read the user-scoped Python 3.11 and
   uv managed-runtime directories. The pinned environment itself is valid when executed
   with normal local permissions; a no-network interpreter probe resolved to the checkout
   `.venv` and Python 3.11.1.
2. The official Xiaohongshu Detail implementation needs `note_id`, `xsec_token`, and
   `xsec_source`. Although the generic CLI help permits a bare ID, its XHS implementation
   obtains the latter two values by parsing the supplied URL. The adapter now accepts the
   selected IDs at the project boundary, resolves each ID back to its tokenized Search URL,
   passes that URL only to the official subprocess, and persists only the IDs in manifests.

The second cause is covered by a regression test that failed before the implementation
change and passed afterward. Tokenized URLs stay in ignored raw files and subprocess
arguments only; they are not printed, committed, or copied into fixtures.

## Verification record

Strict live validation:

```text
uv run python scripts/p0_mediacrawler_probe.py --validate-only ../data/raw/p0-20260906-run-7
P0 artifacts validated: one bound run, 3 Search jobs, and 1 Detail job
VALIDATOR_EXIT=0
```

Fresh implementation verification after the Detail fix:

```text
uv run pytest --basetemp=../data/raw/.pytest-p0-final -q
75 passed in 10.76s

uv run ruff check src tests scripts
All checks passed!

npm test -- --run
1 test passed

npm run lint
exit 0

npm run build
Compiled successfully; static route `/` generated
```

The earlier failed/interrupted raw directories are retained as ignored diagnostic evidence
and are never reused. QR/CAPTCHA was not bypassed. Cookies remain outside Git, the business
database, frontend payloads, fixtures, and ordinary logs.
