# MediaCrawler P0 field report (2026-09-03)

Repository: https://github.com/NanmiCoder/MediaCrawler.git  
Pinned revision: `d6f7c5bb906b6dac40ddf343ef9e26438a3de092`  
Status: **not live-verified**. The shell could not connect to GitHub and no authenticated
MediaCrawler browser session was available. No fixture is committed because fixtures may
only be derived from anonymized real JSONL.

## Field verification

Every field below is `UNVERIFIED` pending live Search/Detail JSONL. No raw-key mapping,
type assumption, or nullable conclusion is made from source inspection alone.

| Contract field | Exact raw key | Example type | Nullable | Decision |
|---|---|---|---|---|
| `note_id` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `title` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `body` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `author_id` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `author_name` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `published_at` | UNVERIFIED | UNVERIFIED | UNVERIFIED | **BLOCKED_FIELD: published_at** |
| `likes` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `collects` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `comments` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `url` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `comment_id` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |
| `comment_content` | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED |

Search engagement `comment_count`, if present in a real note record, is a count and is not
comment content. The validator permits it while rejecting comment record files or embedded
comment records in Search output. Detail must contain only first-level comments, at most 20
per note, for exactly three representative notes.

## Blockers and safety

The requested three Search jobs (`校园足球`, `足球装备`, `大学生体育`) and one Detail job
were not run: GitHub was unreachable from the shell (`Failed to connect to github.com port
443`) and no user-authenticated browser session existed. QR/CAPTCHA was not bypassed.
Formal seven-day implementation must stop at `BLOCKED_FIELD: published_at` until real
records demonstrate a stable timestamp field. Cookies remain outside Git, business DB,
frontend, and ordinary logs.
