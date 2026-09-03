# MediaCrawler P0 field report (2026-09-03)

## Scope and provenance

The integration boundary was reviewed after handoff. `backend/src/crawler/settings.py`
and `adapter.py` were checked against the official repository URL and pinned commit
`d6f7c5bb906b6dac40ddf343ef9e26438a3de092`. The official CLI source confirms the
`search`, `detail`, `get_comment`, `get_sub_comment`, `specified_id`,
`crawler_max_notes_count`, `max_comments_count_singlenotes`, and concurrency options.

The environment could not reach GitHub from the shell and has no authenticated
MediaCrawler browser session. No live Search/Detail output is committed or represented
as real data. The requested three-keyword run therefore remains pending normal user QR
login (or CAPTCHA completion, if shown).

## Field map (fixture shape only; not a live-data claim)

| Contract field | Exact raw key observed/expected in fixture shape | Example type | Nullable | Mapping decision |
|---|---|---|---|---|
| note_id | `note_id` | string | no | preserve as note primary key |
| title | `title` | string | yes | preserve, empty allowed |
| body | `desc` | string | yes | map `desc` to body |
| author_id | `user_id` | string | yes | hash before persistence |
| author_name | `nickname` | string | yes | anonymize in fixtures |
| published_at | `time` | integer | yes | **BLOCKED_FIELD: published_at** until live stability is proven |
| likes | `liked_count` | integer | yes | numeric count, default null |
| collects | `collected_count` | integer | yes | numeric count, default null |
| comments | `comments` | array | yes | Search must be absent/empty; Detail only first-level |
| url | `note_url` | string | yes | require real HTTPS URL in live output |
| comment_id | `comment_id` | string | no | preserve comment key |
| comment_content | `content` | string | yes | map content; anonymize committed fixture |

Because `published_at` could not be checked against live records, formal seven-day
window implementation is blocked. Do not treat fixtures as evidence of field stability.

## Safety constraints

Search uses `get_comment=false`; Detail uses `get_comment=true`, `get_sub_comment=false`,
20 comments per note, and concurrency 1. Cookies are owned by MediaCrawler's local
login state and are excluded from Git, business storage, frontend responses, and normal
logs. QR/CAPTCHA must be completed by the user through the normal flow.
