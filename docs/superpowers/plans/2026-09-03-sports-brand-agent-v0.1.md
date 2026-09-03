# 体育品牌运营 Agent V0.1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 从空白业务结构重建一个使用真实小红书公开数据、评分可解释、证据可追溯并与 V0.4 原型一致的本地单用户体育品牌运营 Agent。

**Architecture:** Next.js 前端只调用 FastAPI REST API；FastAPI 通过独立 Adapter 以子进程调用固定 commit 的 MediaCrawler CLI，标准化 JSONL 后写入独立 SQLite。确定性规则负责热度、趋势、门槛和总分，统一 LLM Service 只负责契约指定的语义任务，并记录 Prompt、模型、输入和结果。

**Tech Stack:** Python 3.12、FastAPI、SQLAlchemy Async、Alembic、SQLite、APScheduler、Pydantic、pytest、Next.js 16、React 19、TypeScript、TanStack Query、Vitest、Testing Library、Playwright。

**Spec:** `docs/superpowers/specs/2026-09-03-sports-brand-agent-v0.1-design.md`

## Global Constraints

- Implementation Contract V0.1 是实现规则的唯一权威；不得修改其中的评分权重、阈值、Topic 身份规则或 LLM/Rule 边界。
- 保留 `.git` 历史；全量移除旧业务实现，但不删除两份外部需求基线文件。
- 不直接 import MediaCrawler 业务类；只通过固定 commit 的 CLI 子进程和 job-specific JSONL 集成。
- MediaCrawler 与 Brand Agent 不共享数据库，Cookie 不进入 Git、业务 SQLite、前端或普通日志。
- 生产演示默认只使用 `real` 数据；`fixture` 与 `demo` 必须明确标记。
- uvicorn 固定单 worker；每次只运行一个 refresh job；采集并发固定为 1。
- 第一轮 Topic Snapshot 的 `trend_score` 必须为 `null`。
- 所有新增业务行为执行测试先行；先观察正确失败，再实现最小代码。
- 当前工作区已有的未提交修改在清理前单独核对；不得静默覆盖。

---

### Task 1: 全量清理与可测试工程骨架

**Files:**
- Delete: `backend/src/agent/`
- Delete: `backend/src/api/v1/agent.py`
- Delete: `backend/src/api/v1/board.py`
- Delete: `backend/src/services/board_service.py`
- Delete: `backend/src/services/task_service.py`
- Delete: `backend/src/models/task.py`
- Delete: `backend/skills/media_crawler/`
- Delete: `frontend/src/components/kanban/`
- Delete: `frontend/src/components/review/`
- Delete: `frontend/src/hooks/useDiscover.ts`
- Delete: `frontend/src/hooks/useStartTask.ts`
- Delete: `frontend/src/hooks/useSubmitFeedback.ts`
- Delete: `frontend/src/hooks/useTaskStatus.ts`
- Delete: `frontend/src/store/kanban.ts`
- Create: `backend/src/app.py`
- Create: `backend/src/api/router.py`
- Create: `backend/src/core/config.py`
- Create: `backend/tests/unit/test_health.py`
- Modify: `backend/pyproject.toml`
- Create: `frontend/src/app/page.test.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- Produces: `create_app() -> FastAPI`, `GET /health`, frontend test/build commands.

- [ ] **Step 1: Record and protect pre-existing edits**

Run: `git status --short` and `git diff -- backend/src/assets/best_practices.md frontend/src/components/kanban/KanbanBoard.tsx`

Expected: exact user-owned edits are visible before their paths are removed. Save them with `git diff --binary --output=data/pre-rewrite-user-changes.patch -- backend/src/assets/best_practices.md frontend/src/components/kanban/KanbanBoard.tsx`, keep the patch untracked, and report its path.

- [ ] **Step 2: Write failing backend health test**

```python
from fastapi.testclient import TestClient

from src.app import create_app


def test_health_reports_service_ready() -> None:
    response = TestClient(create_app()).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "sports-brand-agent"}
```

- [ ] **Step 3: Run backend test and verify RED**

Run: `cd backend; uv run pytest tests/unit/test_health.py -q`

Expected: FAIL because `src.app` does not exist.

- [ ] **Step 4: Remove listed legacy paths and create minimal backend**

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title="体育品牌运营 Agent", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": "sports-brand-agent"}

    return app
```

Add APScheduler, Alembic, PyYAML and test dependencies to `backend/pyproject.toml`. Remove LangGraph, MCP adapters and direct crawler dependencies that are no longer used.

- [ ] **Step 5: Verify backend GREEN**

Run: `cd backend; uv lock; uv run pytest tests/unit/test_health.py -q`

Expected: PASS.

- [ ] **Step 6: Write failing frontend shell test**

```tsx
import { render, screen } from '@testing-library/react'
import Page from './page'

it('renders the five V0.4 workspace modules', () => {
  render(<Page />)
  for (const name of ['热点机会', '内容工作室', '内容日历', '数据复盘', '品牌大脑']) {
    expect(screen.getByRole('button', { name: new RegExp(name) })).toBeInTheDocument()
  }
})
```

- [ ] **Step 7: Run frontend test and verify RED**

Run: `cd frontend; npm test -- --run src/app/page.test.tsx`

Expected: FAIL because the replacement application shell is absent.

- [ ] **Step 8: Add minimal V0.4 shell and test tooling**

Install Vitest, jsdom, Testing Library and Playwright test dependencies. Replace `page.tsx` with a server-safe shell containing the five accessible module buttons; do not add mock metrics or opportunities.

- [ ] **Step 9: Verify Task 1**

Run: `cd backend; uv run pytest -q`

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`

Expected: all commands succeed without warnings caused by application code.

- [ ] **Step 10: Commit**

```bash
git add backend frontend
git commit -m "chore: reset project for v0.1 rebuild"
```

---

### Task 2: P0 MediaCrawler 固定版本与真实字段验证

**Files:**
- Create: `external/README.md`
- Create: `config/mediacrawler.yaml`
- Create: `backend/src/crawler/settings.py`
- Create: `backend/src/crawler/adapter.py`
- Create: `backend/tests/unit/crawler/test_adapter.py`
- Create: `backend/scripts/p0_mediacrawler_probe.py`
- Create: `docs/p0-mediacrawler-field-report.md`
- Create: `tests/fixtures/mediacrawler/search_notes.anonymized.jsonl`
- Create: `tests/fixtures/mediacrawler/detail_notes.anonymized.jsonl`
- Create: `tests/fixtures/mediacrawler/comments.anonymized.jsonl`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `MediaCrawlerSettings`, `MediaCrawlerAdapter.run_search(keyword: str, raw_path: Path) -> CrawlExecution`, `MediaCrawlerAdapter.run_detail(note_ids: list[str], raw_path: Path) -> CrawlExecution`, verified CLI command syntax and field map.

- [ ] **Step 1: Write failing command-construction tests**

```python
def test_search_command_disables_comments_and_limits_raw_notes(settings):
    command = MediaCrawlerAdapter(settings).build_search_command("校园足球", Path("raw"))
    joined = " ".join(command)
    assert "--platform xhs" in joined
    assert "--type search" in joined
    assert "--get_comment false" in joined
    assert "--crawler_max_notes_count 40" in joined
    assert "--max_concurrency_num 1" in joined


def test_detail_command_only_fetches_first_level_comments(settings):
    command = MediaCrawlerAdapter(settings).build_detail_command(["n1", "n2"], Path("detail"))
    joined = " ".join(command)
    assert "--type detail" in joined
    assert "--get_comment true" in joined
    assert "--get_sub_comment false" in joined
    assert "--max_comments_count_singlenotes 20" in joined
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend; uv run pytest tests/unit/crawler/test_adapter.py -q`

Expected: FAIL because crawler settings and adapter do not exist.

- [ ] **Step 3: Clone the official repository and record the tested revision**

Clone `https://github.com/NanmiCoder/MediaCrawler.git` into `external/MediaCrawler`, inspect its current CLI help and repository status, and check out one explicit commit. Do not configure automatic pulls. Keep the external checkout ignored; commit only its repository URL and verified commit in YAML.

- [ ] **Step 4: Implement command construction and subprocess result capture**

```python
@dataclass(frozen=True)
class CrawlExecution:
    started_at: datetime
    finished_at: datetime
    exit_code: int
    raw_path: Path
    stderr_summary: str | None


class MediaCrawlerAdapter:
    async def run_search(self, keyword: str, raw_path: Path) -> CrawlExecution:
        return await self._run(self.build_search_command(keyword, raw_path), raw_path)

    async def run_detail(self, note_ids: list[str], raw_path: Path) -> CrawlExecution:
        return await self._run(self.build_detail_command(note_ids, raw_path), raw_path)
```

Implement `_run(command: list[str], raw_path: Path) -> CrawlExecution` with `asyncio.create_subprocess_exec`; pass each argument separately, set the working directory to the fixed checkout, capture start/end UTC timestamps and exit code, and redact Cookie-like values from the stderr summary.

- [ ] **Step 5: Verify adapter GREEN**

Run: `cd backend; uv run pytest tests/unit/crawler/test_adapter.py -q`

Expected: PASS.

- [ ] **Step 6: Run real P0 search for three sports keywords**

Run the probe with `校园足球`, `足球装备`, and `大学生体育`. If MediaCrawler requests QR login or CAPTCHA, stop at that screen for the user to complete it. Save search JSONL under `data/raw/p0-20260903/` with comments disabled.

- [ ] **Step 7: Run narrow detail probe**

Choose three readable notes from the search output, deduplicate IDs, then execute one detail job with first-level comments enabled and a maximum of 20 comments per note.

- [ ] **Step 8: Produce field report and fixtures**

The report must list the exact raw key, example type, nullable behavior, and mapping decision for `note_id`, `title`, `body`, `author_id`, `author_name`, `published_at`, `likes`, `collects`, `comments`, `url`, `comment_id`, and `comment_content`. Anonymize author identifiers and comment text in committed fixtures while preserving shapes and numeric edge cases.

If `published_at` is unstable, write `BLOCKED_FIELD: published_at` and stop before Task 3.

- [ ] **Step 9: Verify P0 artifacts**

Run: `cd backend; uv run python scripts/p0_mediacrawler_probe.py --validate-only ../data/raw/p0-20260903`

Expected: reports three successful Search jobs, no Search comments, one Detail job, real URLs, and all mandatory field conclusions.

- [ ] **Step 10: Commit**

```bash
git add .gitignore external/README.md config/mediacrawler.yaml backend/src/crawler backend/tests/unit/crawler backend/scripts/p0_mediacrawler_probe.py docs/p0-mediacrawler-field-report.md tests/fixtures/mediacrawler
git commit -m "feat: validate pinned mediacrawler integration"
```

---

### Task 3: 数据库 Schema 与迁移

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/0001_initial_schema.py`
- Create: `backend/src/db/base.py`
- Create: `backend/src/db/session.py`
- Create: `backend/src/db/models.py`
- Create: `backend/tests/integration/test_schema.py`

**Interfaces:**
- Produces: SQLAlchemy models for all contract and supporting tables, `session_factory`, Alembic upgrade path.

- [ ] **Step 1: Write failing schema test**

```python
EXPECTED_TABLES = {
    "refresh_jobs", "notes", "note_snapshots", "note_search_snapshots",
    "topics", "topic_snapshots", "topic_snapshot_notes", "comments", "llm_runs",
    "brand_profiles", "opportunities", "opportunity_llm_runs", "drafts",
    "reject_feedback", "calendar_items", "system_settings",
}


async def test_initial_migration_creates_required_tables(migrated_engine):
    names = set(await inspect_table_names(migrated_engine))
    assert EXPECTED_TABLES <= names
```

Also assert unique constraints for `(job_id, note_id)`, `(job_id, note_id, keyword)`, and `(topic_snapshot_id, note_id)`.

- [ ] **Step 2: Run test and verify RED**

Run: `cd backend; uv run pytest tests/integration/test_schema.py -q`

Expected: FAIL because migrations and tables do not exist.

- [ ] **Step 3: Implement models and migration**

Use UUID strings for externally referenced IDs, UTC-aware datetimes, nullable engagement columns, JSON text columns for raw payloads/metrics, foreign keys for provenance, and indexes on Job status/update time, Topic last-seen time, Opportunity update time and Calendar date.

- [ ] **Step 4: Verify migration GREEN**

Run: `cd backend; uv run alembic upgrade head; uv run pytest tests/integration/test_schema.py -q`

Expected: migration succeeds on a fresh SQLite file and all constraints pass.

- [ ] **Step 5: Commit**

```bash
git add backend/alembic.ini backend/alembic backend/src/db backend/tests/integration/test_schema.py
git commit -m "feat: add traceable v0.1 database schema"
```

---

### Task 4: Normalizer 与 Fixture 导入

**Files:**
- Create: `backend/src/notes/schemas.py`
- Create: `backend/src/notes/normalizer.py`
- Create: `backend/src/notes/repository.py`
- Create: `backend/tests/unit/notes/test_normalizer.py`
- Create: `backend/tests/integration/test_fixture_import.py`

**Interfaces:**
- Produces: `NormalizedNote`, `NormalizedComment`, `normalize_search_record(raw: dict[str, object], captured_at: datetime) -> NormalizedNote`, `normalize_comment_record(raw: dict[str, object], job_id: str) -> NormalizedComment`, `NoteRepository.upsert_refresh_data(job: RefreshJob, notes: list[NormalizedNote]) -> None`.

- [ ] **Step 1: Write failing normalization tests against the P0 fixture**

```python
def test_missing_metrics_remain_none(search_fixture_record, captured_at):
    raw = {**search_fixture_record, "liked_count": None}
    note = normalize_search_record(raw, captured_at)
    assert note.likes is None
    assert note.data_completeness < 1.0


def test_published_at_is_iso_utc(search_fixture_record, captured_at):
    note = normalize_search_record(search_fixture_record, captured_at)
    assert note.published_at is not None
    assert note.published_at.tzinfo is not None
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend; uv run pytest tests/unit/notes/test_normalizer.py -q`

Expected: FAIL because the normalizer does not exist.

- [ ] **Step 3: Implement field mapping and numeric parsing**

`NormalizedNote` must expose the exact contract fields plus `data_completeness`. Treat missing source fields as `None`; only explicit numeric zero stays zero. Parse Chinese compact counts deterministically and reject negative engagement values.

- [ ] **Step 4: Verify unit GREEN**

Run: `cd backend; uv run pytest tests/unit/notes/test_normalizer.py -q`

Expected: PASS.

- [ ] **Step 5: Write and run failing fixture-import test**

The test imports the three P0 fixtures into a temporary database and asserts stable note IDs, one snapshot per Job/Note, one search position per Job/Note/Keyword, and preserved nullable metrics.

Run: `cd backend; uv run pytest tests/integration/test_fixture_import.py -q`

Expected: FAIL before repository implementation, then PASS after implementing transactional upserts.

- [ ] **Step 6: Commit**

```bash
git add backend/src/notes backend/tests/unit/notes backend/tests/integration/test_fixture_import.py
git commit -m "feat: normalize and persist mediacrawler records"
```

---

### Task 5: Refresh 状态机、两阶段采集与调度

**Files:**
- Create: `backend/src/refresh/status.py`
- Create: `backend/src/refresh/service.py`
- Create: `backend/src/refresh/scheduler.py`
- Create: `backend/tests/unit/refresh/test_lock.py`
- Create: `backend/tests/unit/refresh/test_recovery.py`
- Create: `backend/tests/integration/test_two_pass_refresh.py`

**Interfaces:**
- Produces: `RefreshService.start(mode) -> RefreshJob`, `RefreshAlreadyRunning`, `recover_stale_jobs(now)`, `configure_scheduler(app)`.
- Consumes: `MediaCrawlerAdapter`, Normalizer and repositories.

- [ ] **Step 1: Write failing lock and recovery tests**

```python
async def test_second_refresh_is_rejected(refresh_service):
    running = await refresh_service.start("manual")
    with pytest.raises(RefreshAlreadyRunning) as error:
        await refresh_service.start("manual")
    assert error.value.running_job_id == running.id


async def test_stale_running_job_becomes_interrupted(refresh_repo, now):
    job = await refresh_repo.create(status="normalizing", updated_at=now - timedelta(minutes=31))
    await recover_stale_jobs(refresh_repo, now)
    assert (await refresh_repo.get(job.id)).status == "interrupted"
```

- [ ] **Step 2: Verify RED**

Run: `cd backend; uv run pytest tests/unit/refresh -q`

Expected: FAIL because refresh services do not exist.

- [ ] **Step 3: Implement state transitions and single-process lock**

Allow only the exact contract statuses. Persist every transition and `updated_at`. Return `REFRESH_ALREADY_RUNNING` with the active ID. On startup, recover stale queued/working jobs older than 30 minutes.

- [ ] **Step 4: Write failing two-pass integration test**

Use a fake process runner returning the committed real-shape fixtures. Assert six independent Search calls, zero Search comments, filtering to seven days and 20 notes per keyword, Topic resolution boundary, then Detail calls only for deduplicated representative IDs with at most five notes per Topic.

- [ ] **Step 5: Implement two-pass orchestration**

Persist raw execution metadata per keyword. Continue successful keywords after individual failures and set `partial_success`; set `failed` only when no keyword succeeds. Never promote the raw JSONL directly to API output.

- [ ] **Step 6: Implement APScheduler behavior**

Configure local-time runs at 09:00, 15:00 and 21:00, no startup catch-up, and disable auto-refresh after two consecutive scheduled failures.

- [ ] **Step 7: Verify Task 5**

Run: `cd backend; uv run pytest tests/unit/refresh tests/integration/test_two_pass_refresh.py -q`

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/src/refresh backend/tests/unit/refresh backend/tests/integration/test_two_pass_refresh.py
git commit -m "feat: orchestrate locked two-pass refresh jobs"
```

---

### Task 6: Topic 身份、代表笔记与生命周期

**Files:**
- Create: `backend/src/topics/schemas.py`
- Create: `backend/src/topics/identity.py`
- Create: `backend/src/topics/representatives.py`
- Create: `backend/src/topics/lifecycle.py`
- Create: `backend/src/topics/repository.py`
- Create: `backend/tests/unit/topics/test_identity.py`
- Create: `backend/tests/unit/topics/test_representatives.py`
- Create: `backend/tests/unit/topics/test_lifecycle.py`

**Interfaces:**
- Produces: `TopicSemanticResolver` protocol, `resolve_topic(candidate: CandidateCluster, topics: list[TopicCandidate], resolver: TopicSemanticResolver) -> TopicResolution`, `choose_representatives(notes: list[CandidateNote], limit: int = 3) -> list[CandidateNote]`, `classify_lifecycle(history: list[TopicSnapshot], current: TopicSnapshot) -> Lifecycle`, repository snapshot methods.
- Consumes: an injected `TopicSemanticResolver`; unit tests use a deterministic fake, and Task 8 makes `LLMService` implement the protocol.

- [ ] **Step 1: Write failing overlap tests**

Assert that overlap below two returns no rule match, overlap of two matches the existing Topic, multiple matches select highest Jaccard similarity, only Topics seen within 14 days participate, and a matched Topic ID never changes when its canonical name changes.

- [ ] **Step 2: Verify RED**

Run: `cd backend; uv run pytest tests/unit/topics/test_identity.py -q`

Expected: FAIL because Topic identity functions do not exist.

- [ ] **Step 3: Implement rule identity and persistence**

Use semantic resolution only when overlap provides no result; accept `MATCH_EXISTING` only at confidence `>= 0.80`, otherwise create a UUID Topic.

- [ ] **Step 4: Write failing representative and lifecycle tests**

Representatives must prioritize relevance, richer engagement, author diversity, recency and readable detail, default to three and cap at five. Lifecycle tests must cover Observing, Emerging, Growing, Peak, Declining and three-refresh Expired exactly in priority order.

- [ ] **Step 5: Implement and verify GREEN**

Run: `cd backend; uv run pytest tests/unit/topics -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/topics backend/tests/unit/topics
git commit -m "feat: preserve topic identity across refreshes"
```

---

### Task 7: Current Heat、Trend Score 与 Confidence

**Files:**
- Create: `backend/src/scoring/metrics.py`
- Create: `backend/src/scoring/percentiles.py`
- Create: `backend/src/scoring/heat.py`
- Create: `backend/src/scoring/trend.py`
- Create: `backend/src/scoring/confidence.py`
- Create: `backend/tests/unit/scoring/test_heat.py`
- Create: `backend/tests/unit/scoring/test_trend.py`
- Create: `backend/tests/unit/scoring/test_confidence.py`

**Interfaces:**
- Produces: pure functions `weighted_engagement`, `normalize_percentiles`, `current_heat`, `trend_metrics`, `trend_score`, `classify_confidence`.

- [ ] **Step 1: Write failing heat tests**

```python
def test_weighted_engagement_uses_contract_weights():
    assert weighted_engagement(likes=10, collects=4, comments=3) == 22


def test_unavailable_comment_demand_reweights_remaining_metrics():
    normalized = {"engagement": 100, "freshness": 0, "volume": 0, "creator_spread": 0, "comment_demand": None}
    assert current_heat(normalized) == pytest.approx(35 / 90 * 100)
```

Also test median `log1p`, `exp(-age_hours / 72)`, volume, spread, comment samples below ten, tied percentiles and raw/normalized metric preservation.

- [ ] **Step 2: Verify RED, implement and verify GREEN**

Run: `cd backend; uv run pytest tests/unit/scoring/test_heat.py -q`

Expected: FAIL before implementation, PASS after the smallest formula implementation.

- [ ] **Step 3: Write failing trend tests**

Cover first snapshot returning `None`, exact 20→10 and 5→10 search-position momentum, shared-note engagement delta clamped at zero, per-24-hour velocities, four-refresh persistence and creator expansion.

- [ ] **Step 4: Implement trend formula and verify GREEN**

Run: `cd backend; uv run pytest tests/unit/scoring/test_trend.py -q`

Expected: PASS with contract weights 25/25/20/15/15.

- [ ] **Step 5: Write and implement Confidence tests**

Cover every High requirement, Medium minimum, Low conditions, comment independence and partial-success penalty. Do not ask the LLM to classify confidence.

- [ ] **Step 6: Verify Task 7**

Run: `cd backend; uv run pytest tests/unit/scoring -q`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/scoring backend/tests/unit/scoring
git commit -m "feat: implement explainable heat and trend scoring"
```

---

### Task 8: 统一 LLM Service、Schema、Prompt 和追踪

**Files:**
- Create: `backend/src/llm/service.py`
- Create: `backend/src/llm/client.py`
- Create: `backend/src/llm/schemas.py`
- Create: `backend/src/llm/repository.py`
- Create: `backend/prompts/topic_cluster_v1.md`
- Create: `backend/prompts/topic_resolution_v1.md`
- Create: `backend/prompts/comment_analysis_v1.md`
- Create: `backend/prompts/opportunity_scoring_v1.md`
- Create: `backend/prompts/opportunity_explanation_v1.md`
- Create: `backend/prompts/copy_preview_v1.md`
- Create: `backend/prompts/full_copy_v1.md`
- Create: `backend/tests/unit/llm/test_service.py`

**Interfaces:**
- Produces: all ten methods required by the contract on `LLMService` and typed Pydantic response schemas.

- [ ] **Step 1: Write failing retry and trace tests**

```python
async def test_schema_failure_retries_once_and_records_failure(service, client, llm_run_repo):
    client.responses = ["not-json", '{"still":"invalid"}']
    with pytest.raises(LLMAnalysisUnavailable):
        await service.analyze_comments(job_id="j1", topic_id="t1", comments=[])
    run = await llm_run_repo.latest()
    assert client.call_count == 2
    assert run.status == "failed"
    assert run.prompt_version == "comment_analysis_v1"
```

Also assert `input_hash`, model, schema version, temperature, raw response, parsed response and error persistence.

- [ ] **Step 2: Verify RED**

Run: `cd backend; uv run pytest tests/unit/llm/test_service.py -q`

Expected: FAIL because the service does not exist.

- [ ] **Step 3: Implement client boundary and prompt loader**

Only `llm/client.py` may know the provider SDK/HTTP API. Business modules call `LLMService`. Load prompt files by version; reject a missing prompt rather than embedding fallback prompt text in Python.

- [ ] **Step 4: Implement Pydantic JSON schemas**

Schemas must include evidence note/comment IDs where required. Validate all evidence IDs against the input set and reject invented IDs. Comment categories must use the six contract enums.

- [ ] **Step 5: Verify Task 8**

Run: `cd backend; uv run pytest tests/unit/llm -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/llm backend/prompts backend/tests/unit/llm
git commit -m "feat: centralize traceable structured llm calls"
```

---

### Task 9: Brand Brain、Eligibility 与 Opportunity Engine

**Files:**
- Create: `backend/src/brand/schemas.py`
- Create: `backend/src/brand/service.py`
- Create: `backend/src/opportunities/schemas.py`
- Create: `backend/src/opportunities/gates.py`
- Create: `backend/src/opportunities/scoring.py`
- Create: `backend/src/opportunities/service.py`
- Create: `backend/tests/unit/brand/test_versioning.py`
- Create: `backend/tests/unit/opportunities/test_gates.py`
- Create: `backend/tests/unit/opportunities/test_scoring.py`
- Create: `backend/tests/integration/test_opportunity_provenance.py`

**Interfaces:**
- Produces: `BrandService.update(profile: BrandProfileInput) -> BrandProfile`, `evaluate_eligibility(context: EligibilityContext) -> EligibilityResult`, `trend_timing(current_heat: float, trend_score: float | None, lifecycle: Lifecycle) -> float`, `opportunity_score(scores: OpportunityDimensions) -> float`, `OpportunityService.analyze_topic(topic_snapshot_id: str) -> Opportunity`.

- [ ] **Step 1: Write failing Brand Brain version test**

Assert every saved modification creates version `previous + 1`, validates traffic/brand/product percentages total 100, and never mutates the profile version stored on an existing Opportunity or Draft.

- [ ] **Step 2: Implement Brand Brain and verify GREEN**

Run: `cd backend; uv run pytest tests/unit/brand/test_versioning.py -q`

Expected: PASS.

- [ ] **Step 3: Write failing Gate tests**

Cover high brand-safety risk, Expired, combined brand `<25` and product `<20`, recent duplicate becoming `manual_review`, and ordering before Opportunity score.

- [ ] **Step 4: Implement Gates and verify GREEN**

Run: `cd backend; uv run pytest tests/unit/opportunities/test_gates.py -q`

Expected: PASS.

- [ ] **Step 5: Write failing scoring tests**

Assert weights 30/20/20/20/10, trend timing lifecycle adjustments, first-refresh timing capped at 70, decision boundaries 80/65/50, Filtered precedence and at most two content goals.

- [ ] **Step 6: Implement Opportunity aggregation**

Persist all five inputs, reasons, evidence IDs, Topic Snapshot, Brand Profile version, related LLM Runs, source notes and data source. Do not create an Opportunity score if mandatory LLM dimensions are unavailable.

- [ ] **Step 7: Verify provenance integration**

Run: `cd backend; uv run pytest tests/unit/opportunities tests/integration/test_opportunity_provenance.py -q`

Expected: every Opportunity traces to Topic Snapshot → Note Snapshot → source URL and LLM Run → Prompt/Model/Brand version.

- [ ] **Step 8: Commit**

```bash
git add backend/src/brand backend/src/opportunities backend/tests/unit/brand backend/tests/unit/opportunities backend/tests/integration/test_opportunity_provenance.py
git commit -m "feat: add gated evidence-backed opportunities"
```

---

### Task 10: Copy Preview、Accept、Reject、Draft 与 Calendar

**Files:**
- Create: `backend/src/content/schemas.py`
- Create: `backend/src/content/service.py`
- Create: `backend/src/content/repository.py`
- Create: `backend/tests/unit/content/test_preview.py`
- Create: `backend/tests/integration/test_accept_reject_calendar.py`

**Interfaces:**
- Produces: `generate_preview(opportunity_id)`, `accept_opportunity(id) -> Draft`, `reject_opportunity(id, reason)`, `schedule_draft(draft_id, when)`.

- [ ] **Step 1: Write failing preview tests**

Assert exactly three titles, one 80–150 Chinese-character preview body, format, tag direction, cover direction, product connection and cost; reject a long-form preview.

- [ ] **Step 2: Implement preview and verify GREEN**

Run: `cd backend; uv run pytest tests/unit/content/test_preview.py -q`

Expected: PASS.

- [ ] **Step 3: Write failing workflow test**

Accept must create a full Draft containing three titles, body, tags, CTA, cover text, image count/advice, product connection and risk check, with source Opportunity, Topic, Brand version and Prompt version. Reject must accept only the eight contract enums and must not change model settings. A Draft must be schedulable into Calendar.

- [ ] **Step 4: Implement workflow and verify GREEN**

Run: `cd backend; uv run pytest tests/integration/test_accept_reject_calendar.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/src/content backend/tests/unit/content backend/tests/integration/test_accept_reject_calendar.py
git commit -m "feat: convert opportunities into scheduled drafts"
```

---

### Task 11: FastAPI Contract 与降级响应

**Files:**
- Create: `backend/src/api/errors.py`
- Create: `backend/src/api/refresh.py`
- Create: `backend/src/api/opportunities.py`
- Create: `backend/src/api/brand.py`
- Create: `backend/src/api/content.py`
- Create: `backend/src/api/analytics.py`
- Modify: `backend/src/api/router.py`
- Modify: `backend/src/app.py`
- Create: `backend/tests/integration/api/test_refresh.py`
- Create: `backend/tests/integration/api/test_opportunities.py`
- Create: `backend/tests/integration/api/test_degraded.py`

**Interfaces:**
- Produces: REST endpoints listed in the design and camelCase Opportunity response matching the contract.

- [ ] **Step 1: Write failing Opportunity API contract test**

Assert the response contains `id`, `topicId`, `currentHeat`, nullable `trendScore`, `trendStage`, `score`, `decision`, `goal`, `eligibility`, `risk`, `confidence`, five score components, reasons, sources, preview, `updatedAt` and `data_source`.

- [ ] **Step 2: Write failing refresh conflict test**

Assert the second `POST /api/refresh-jobs` returns HTTP 409 and exactly `{"code":"REFRESH_ALREADY_RUNNING","running_job_id":"job-running-1"}` for a seeded running Job with ID `job-running-1`.

- [ ] **Step 3: Implement thin routers and error mapping**

Dependency-inject services; keep calculations outside route handlers. Use explicit Pydantic response models and consistent UTC ISO-8601 serialization.

- [ ] **Step 4: Write and implement degraded response tests**

Cover latest successful snapshot fallback with actual old `updatedAt`, no-history unavailable response, partial success metadata, `analysis_unavailable`, rejected Filtered accept, and `fixture`/`demo` labels.

- [ ] **Step 5: Verify Task 11**

Run: `cd backend; uv run pytest tests/integration/api -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/src/api backend/src/app.py backend/tests/integration/api
git commit -m "feat: expose v0.1 application api"
```

---

### Task 12: V0.4 前端基础与热点机会闭环

**Files:**
- Create: `frontend/src/features/shared/api.ts`
- Create: `frontend/src/features/shared/types.ts`
- Create: `frontend/src/features/shared/DataSourceBadge.tsx`
- Create: `frontend/src/features/layout/AppShell.tsx`
- Create: `frontend/src/features/opportunities/OpportunityPage.tsx`
- Create: `frontend/src/features/opportunities/OpportunityList.tsx`
- Create: `frontend/src/features/opportunities/OpportunityDetail.tsx`
- Create: `frontend/src/features/opportunities/DecisionPanel.tsx`
- Create: `frontend/src/features/opportunities/CopyPreview.tsx`
- Create: `frontend/src/features/opportunities/useOpportunities.ts`
- Create: `frontend/src/features/opportunities/OpportunityPage.test.tsx`
- Modify: `frontend/src/app/page.tsx`
- Modify: `frontend/src/app/globals.css`

**Interfaces:**
- Produces: V0.4-aligned three-column opportunity decision page backed only by `/api`.

- [ ] **Step 1: Write failing page-state tests**

Test real opportunity rendering, source links, captured time, Current Heat, nullable Trend Score message, lifecycle, confidence, full/partial failure banners, analysis unavailable retry, real/fixture/demo badges, Filtered disabled accept, accept navigation and reject enum submission.

- [ ] **Step 2: Verify RED**

Run: `cd frontend; npm test -- --run src/features/opportunities/OpportunityPage.test.tsx`

Expected: FAIL because feature components do not exist.

- [ ] **Step 3: Implement typed API layer and query hooks**

Map API errors to explicit UI states. Never synthesize scores, sources, counts or update times in the browser.

- [ ] **Step 4: Implement V0.4 decision page**

Reproduce the prototype's forest sidebar, paper surfaces, coral actions, opportunity list, decision detail, human decision panel, copy preview and content brief. Use responsive breakpoints so the three columns stack without hiding source or decision information.

- [ ] **Step 5: Verify Task 12**

Run: `cd frontend; npm test -- --run src/features/opportunities/OpportunityPage.test.tsx; npm run lint; npm run build`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/src frontend/package.json frontend/package-lock.json
git commit -m "feat: connect v0.4 opportunity workspace"
```

---

### Task 13: Content Studio、Calendar、Analytics 与 Brand Brain

**Files:**
- Create: `frontend/src/features/studio/StudioPage.tsx`
- Create: `frontend/src/features/studio/StudioPage.test.tsx`
- Create: `frontend/src/features/calendar/CalendarPage.tsx`
- Create: `frontend/src/features/calendar/CalendarPage.test.tsx`
- Create: `frontend/src/features/analytics/AnalyticsPage.tsx`
- Create: `frontend/src/features/analytics/AnalyticsPage.test.tsx`
- Create: `frontend/src/features/brand/BrandPage.tsx`
- Create: `frontend/src/features/brand/BrandPage.test.tsx`
- Modify: `frontend/src/features/layout/AppShell.tsx`

**Interfaces:**
- Produces: remaining four V0.4 modules using real API state.

- [ ] **Step 1: Write failing Content Studio tests**

Assert accepted Draft rendering, editable fields, candidate AI version not overwriting original until accepted, risk result, image advice and Calendar submission.

- [ ] **Step 2: Implement Studio and verify GREEN**

Run: `cd frontend; npm test -- --run src/features/studio/StudioPage.test.tsx`

Expected: PASS.

- [ ] **Step 3: Write failing Calendar tests**

Assert month/week modes, goal/status filters, editable date/time/status, Draft provenance and no auto-publish control.

- [ ] **Step 4: Implement Calendar and verify GREEN**

Run: `cd frontend; npm test -- --run src/features/calendar/CalendarPage.test.tsx`

Expected: PASS.

- [ ] **Step 5: Write failing Analytics tests**

Assert real published metrics when present and explicit unavailable state when absent. Fixture or demo analytics must display its label.

- [ ] **Step 6: Implement Analytics and verify GREEN**

Run: `cd frontend; npm test -- --run src/features/analytics/AnalyticsPage.test.tsx`

Expected: PASS.

- [ ] **Step 7: Write failing Brand Brain tests**

Assert foundation, audiences, scenes, tone, forbidden rules, strategy total validation, product fields, save confirmation and visible version increment.

- [ ] **Step 8: Implement Brand Brain and verify GREEN**

Run: `cd frontend; npm test -- --run src/features/brand/BrandPage.test.tsx`

Expected: PASS.

- [ ] **Step 9: Verify Task 13**

Run: `cd frontend; npm test -- --run; npm run lint; npm run build`

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add frontend/src/features
git commit -m "feat: complete v0.4 content workspace modules"
```

---

### Task 14: 端到端坏案例、视觉核对与运行文档

**Files:**
- Create: `frontend/e2e/opportunity-flow.spec.ts`
- Create: `frontend/e2e/degraded-states.spec.ts`
- Create: `backend/tests/integration/test_refresh_end_to_end.py`
- Modify: `README.md`
- Create: `.env.example`
- Create: `docs/demo-runbook.md`

**Interfaces:**
- Produces: repeatable local startup, login, refresh, demo and failure-recovery workflow.

- [ ] **Step 1: Write failing backend end-to-end test**

Run two fixture-backed refreshes and assert stable Topic ID, first `trend_score=None`, second numeric Trend Score, raw and normalized metrics, three source links, Opportunity provenance, Accept → Draft → Calendar and structured Reject.

- [ ] **Step 2: Verify RED, complete missing wiring and verify GREEN**

Run: `cd backend; uv run pytest tests/integration/test_refresh_end_to_end.py -q`

Expected: FAIL before final wiring, then PASS.

- [ ] **Step 3: Write browser tests**

The happy-path test starts refresh, waits for completion, opens an Opportunity, verifies three source links, accepts it, opens the Draft and schedules it. The degraded test covers old snapshot, partial success, analysis unavailable and fixture/demo labels.

- [ ] **Step 4: Run browser tests and repair only observed failures**

Run: `cd frontend; npx playwright test`

Expected: all tests pass at desktop and a mobile viewport.

- [ ] **Step 5: Visually compare against V0.4**

Render the implemented five modules and compare layout, hierarchy, typography, colors, states and interactions to the supplied HTML. Fix discrepancies that alter the approved V0.4 experience; do not introduce a new design system.

- [ ] **Step 6: Write operational documentation**

README and runbook must include prerequisites, pinned MediaCrawler location/commit, normal QR login, environment variables, database migration, one-worker backend startup, frontend startup, manual refresh, scheduled times, real/fixture/demo labels, reset procedure, degraded states and the exact demo sequence.

- [ ] **Step 7: Run complete verification**

Run: `cd backend; uv run ruff check .; uv run mypy src; uv run pytest -q`

Run: `cd frontend; npm test -- --run; npm run lint; npm run build; npx playwright test`

Expected: every command exits 0 with no application warnings.

- [ ] **Step 8: Audit Definition of Done**

Check all 22 items from Implementation Contract section 33 against test output and stored artifacts. Record each as PASS with its evidence command/file. Any unmet item must be recorded as BLOCKED, DEGRADED or UNAVAILABLE with its real cause; no synthetic result may close the item.

- [ ] **Step 9: Commit**

```bash
git add README.md .env.example docs/demo-runbook.md backend/tests/integration/test_refresh_end_to_end.py frontend/e2e
git commit -m "test: verify v0.1 end-to-end operation"
```
