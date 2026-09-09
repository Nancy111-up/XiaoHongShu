# Final fix wave report

Date: 2026-09-09

## Implemented

- Refresh collection reads the pinned MediaCrawler XHS JSONL layout (`xhs/jsonl/*_contents_<date>.jsonl`) while retaining legacy fixture compatibility, and skips the detail pass when successful searches contain no notes.
- Signed XHS search URLs remain in memory only for the detail subprocess; persisted/API URLs and normalized raw payloads stay query-free.
- FastAPI lifespan startup recovers stale active refresh jobs and releases the single active slot.
- Windows startup documentation uses Uvicorn without reload so asyncio subprocess creation remains available.
- Opportunity previews are persisted in the UI contract (`titles`, `angle`, `body`, directions and CTA) rather than the raw LLM response contract.
- Full-copy generation loads the opportunity's exact brand profile version plus only its source notes/comments, and passes explicit note/comment ID allowlists to the LLM service.
- Reject and existing-draft scheduling remain available without AI; accept returns a safe 503.
- The opportunity header reads the real draft total from analytics, and populated partial refreshes display a partial-live badge.

## Verification

- Focused backend regression set: 19 passed.
- No-AI API regression: 1 passed.
- Full backend tests: 181 passed.
- Backend Ruff: passed.
- Backend mypy (`src`): passed, 59 source files.
- Full frontend tests: 36 passed across 3 files.
- Frontend ESLint: passed.
- Frontend Next.js production build: passed.

## Remaining concerns

- Live QR login, Xiaohongshu responses, and the configured external LLM still require local operator acceptance testing; automated tests use controlled boundary substitutes and do not claim third-party availability.
- Refresh execution remains intentionally single-process and single-active-job; this release does not add a durable queue or high-concurrency workers.
