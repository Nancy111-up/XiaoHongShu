# Live Workspace Data Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the empty workspace into a real MediaCrawler-to-opportunity-to-content workflow with visible progress and actionable downstream modules.

**Architecture:** A FastAPI in-process background runner consumes each persisted refresh job, executes the existing pinned MediaCrawler adapter and two-pass coordinator, then creates evidence-backed opportunities. The Next.js client polls the job resource and reloads real records when work finishes; every module renders loading, empty, error, and populated states from API data.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, SQLite, MediaCrawler CLI, pytest, TypeScript, React 19, Next.js 16, Vitest, Testing Library.

**Spec:** `docs/superpowers/specs/2026-09-08-live-workspace-data-loop-design.md`

## Global Constraints

- Use only the pinned official `NanmiCoder/MediaCrawler` checkout already configured by the project.
- Never expose cookies, tokens, browser credentials, or raw crawler stderr.
- Never label fixture, test, or invented data as real data.
- Permit only one active refresh job.
- Keep raw collection output in the ignored project data directory.
- Do not add a queue service or automatic social publishing in V0.1.

---

### Task 1: Executable Refresh Boundary

**Files:**
- Create: `backend/src/refresh/runner.py`
- Modify: `backend/src/api/refresh.py`
- Modify: `backend/src/api/router.py`
- Modify: `backend/src/app.py`
- Test: `backend/tests/integration/api/test_refresh.py`

**Interfaces:**
- Consumes: `TwoPassRefreshCoordinator.run(job, keywords, raw_root, now)` and `RefreshRepository`.
- Produces: `RefreshRunner.start(job_id: str) -> None` and injected `run_refresh(job_id: str) -> Awaitable[None]` for the API router.

- [ ] **Step 1: Write the failing background-start test**

```python
def test_creating_refresh_dispatches_runner(tmp_path):
    dispatched = []
    app = create_app_for_test(tmp_path, run_refresh=lambda job_id: dispatched.append(job_id))
    response = TestClient(app).post("/api/refresh-jobs")
    assert response.status_code == 202
    assert dispatched == [response.json()["id"]]
```

- [ ] **Step 2: Run the focused test and verify it fails**

Run: `python -m pytest tests/integration/api/test_refresh.py -q`
Expected: FAIL because the API does not dispatch a runner.

- [ ] **Step 3: Implement dependency-injected background execution**

Create a focused `RefreshRunner` that loads the job, reads brand-derived keywords, builds a per-job raw path, calls the existing coordinator, and catches exceptions by transitioning the job to `failed`. Pass its callable through `create_app` → `build_api_router` → `build_refresh_router`; use FastAPI `BackgroundTasks.add_task` after persistence.

- [ ] **Step 4: Verify refresh API behavior**

Run: `python -m pytest tests/integration/api/test_refresh.py tests/unit/refresh/test_status.py -q`
Expected: PASS, including the existing 409 concurrent-refresh contract.

- [ ] **Step 5: Commit**

```bash
git add backend/src/refresh/runner.py backend/src/api/refresh.py backend/src/api/router.py backend/src/app.py backend/tests/integration/api/test_refresh.py
git commit -m "feat: execute refresh jobs in background"
```

### Task 2: Observable Refresh Status

**Files:**
- Modify: `backend/src/api/refresh.py`
- Modify: `backend/src/db/models.py`
- Create: `backend/alembic/versions/0002_refresh_error_summary.py`
- Modify: `backend/src/refresh/status.py`
- Test: `backend/tests/integration/api/test_refresh.py`

**Interfaces:**
- Consumes: persisted `RefreshJob` status and keyword result fields.
- Produces: `GET /api/refresh-jobs/{id}` with `status`, `successfulKeywords`, `failedKeywords`, `errorSummary`, and `updatedAt`.

- [ ] **Step 1: Write the failing response-contract test**

```python
payload = client.get(f"/api/refresh-jobs/{job_id}").json()
assert payload.keys() >= {"id", "status", "successfulKeywords", "failedKeywords", "errorSummary", "updatedAt"}
```

- [ ] **Step 2: Run the contract test and verify it fails**

Run: `python -m pytest tests/integration/api/test_refresh.py -q`
Expected: FAIL because progress detail is absent.

- [ ] **Step 3: Add persisted sanitized error detail and API mapping**

Add nullable `error_summary` to the model and migration. Add `RefreshRepository.fail(job_id, safe_summary, now)`; ensure the runner passes crawler errors through `redact_sensitive_text` and caps summaries at 300 characters. Decode existing JSON keyword fields in the API response.

- [ ] **Step 4: Verify status and redaction tests**

Run: `python -m pytest tests/integration/api/test_refresh.py tests/unit/refresh/test_status.py tests/unit/crawler/test_adapter.py -q`
Expected: PASS with no secret value in response assertions.

- [ ] **Step 5: Commit**

```bash
git add backend/src/api/refresh.py backend/src/db/models.py backend/alembic/versions/0002_refresh_error_summary.py backend/src/refresh/status.py backend/tests/integration/api/test_refresh.py
git commit -m "feat: expose refresh progress and safe failures"
```

### Task 3: Evidence-Backed Opportunity Production

**Files:**
- Create: `backend/src/opportunities/pipeline.py`
- Modify: `backend/src/refresh/runner.py`
- Modify: `backend/src/opportunities/service.py`
- Test: `backend/tests/integration/test_refresh_to_opportunities.py`

**Interfaces:**
- Consumes: normalized notes and topic representatives persisted for a completed collection pass.
- Produces: `OpportunityPipeline.build(job_id: str) -> list[Opportunity]` and database rows readable by `GET /api/opportunities`.

- [ ] **Step 1: Write the failing end-to-end persistence test**

```python
await runner.run(job.id)
response = client.get("/api/opportunities")
assert response.json()["data_source"] == "real"
assert response.json()["items"][0]["sourceLinks"]
```

- [ ] **Step 2: Run the new integration test and verify it fails**

Run: `python -m pytest tests/integration/test_refresh_to_opportunities.py -q`
Expected: FAIL because collection does not invoke opportunity production.

- [ ] **Step 3: Implement the opportunity pipeline**

Load topic evidence for the job, compute deterministic heat/trend/confidence inputs through existing scoring modules, call `OpportunityService.create` for eligible topics, and preserve note/LLM provenance. If AI configuration is absent, return partial success with the collected notes intact and a safe `error_summary` explaining that AI configuration is required.

- [ ] **Step 4: Verify provenance and pipeline integration**

Run: `python -m pytest tests/integration/test_refresh_to_opportunities.py tests/integration/test_opportunity_provenance.py tests/integration/api/test_opportunities.py -q`
Expected: PASS; every returned opportunity traces to source evidence.

- [ ] **Step 5: Commit**

```bash
git add backend/src/opportunities/pipeline.py backend/src/refresh/runner.py backend/src/opportunities/service.py backend/tests/integration/test_refresh_to_opportunities.py
git commit -m "feat: generate opportunities from refresh evidence"
```

### Task 4: Frontend Refresh Progress

**Files:**
- Modify: `frontend/src/features/shared/types.ts`
- Modify: `frontend/src/features/shared/api.ts`
- Modify: `frontend/src/features/opportunities/useOpportunities.ts`
- Modify: `frontend/src/features/opportunities/OpportunityPage.tsx`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/features/opportunities/OpportunityPage.test.tsx`

**Interfaces:**
- Consumes: `POST /refresh-jobs` job ID and expanded `GET /refresh-jobs/{id}` payload.
- Produces: `refreshState` containing job ID, stage label, terminal state, failed keywords, and safe error message.

- [ ] **Step 1: Write the failing polling UI test**

```tsx
await user.click(screen.getByRole("button", { name: /刷新热点/ }))
expect(await screen.findByText("正在采集搜索结果")).toBeInTheDocument()
expect(await screen.findByText("刷新完成")).toBeInTheDocument()
expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/refresh-jobs/job-1"), expect.anything())
```

- [ ] **Step 2: Run the focused frontend test and verify it fails**

Run: `npm test -- OpportunityPage.test.tsx`
Expected: FAIL because the client neither retains nor polls the job ID.

- [ ] **Step 3: Implement status polling and clear empty-state guidance**

Return `{id,status}` from `startRefresh`, add `getRefreshJob`, poll every 1500 ms until a terminal state, map backend stages to Chinese labels, reload opportunities after success, and show login/configuration/failure actions without fabricating records. Disable refresh while active.

- [ ] **Step 4: Verify the frontend flow**

Run: `npm test -- OpportunityPage.test.tsx`
Expected: PASS for queued, running, completed, partial, and failed scenarios.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/shared/types.ts frontend/src/features/shared/api.ts frontend/src/features/opportunities/useOpportunities.ts frontend/src/features/opportunities/OpportunityPage.tsx frontend/src/app/globals.css frontend/src/features/opportunities/OpportunityPage.test.tsx
git commit -m "feat: show live refresh progress"
```

### Task 5: Populated Downstream Workspaces

**Files:**
- Create: `frontend/src/features/workspace/ContentStudio.tsx`
- Create: `frontend/src/features/workspace/ContentCalendar.tsx`
- Create: `frontend/src/features/workspace/AnalyticsDashboard.tsx`
- Create: `frontend/src/features/workspace/BrandBrain.tsx`
- Modify: `frontend/src/features/opportunities/OpportunityPage.tsx`
- Modify: `frontend/src/features/shared/api.ts`
- Modify: `frontend/src/app/globals.css`
- Test: `frontend/src/features/opportunities/OpportunityPage.test.tsx`

**Interfaces:**
- Consumes: existing `/drafts`, `/calendar`, `/analytics`, and `/brand-profile` resources.
- Produces: four focused React module components with loading, populated, empty, and error states.

- [ ] **Step 1: Write failing populated-module tests**

```tsx
await user.click(screen.getByRole("button", { name: /内容工作室/ }))
expect(await screen.findByText("校园足球装备清单")).toBeInTheDocument()
await user.click(screen.getByRole("button", { name: /数据复盘/ }))
expect(await screen.findByText("机会转化率")).toBeInTheDocument()
```

- [ ] **Step 2: Run the module tests and verify they fail**

Run: `npm test -- OpportunityPage.test.tsx`
Expected: FAIL because the generic module view does not render returned records.

- [ ] **Step 3: Implement focused real-data modules**

Move each module out of `OpportunityPage.tsx`. Render draft title/status/actions, calendar date/status, analytics counts and conversion ratio, and the versioned brand profile form. Keep empty-state calls to action linked to the upstream step that creates the missing record.

- [ ] **Step 4: Verify module rendering and interaction**

Run: `npm test -- OpportunityPage.test.tsx`
Expected: PASS for navigation, populated responses, empty states, failures, and brand save.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/features/workspace frontend/src/features/opportunities/OpportunityPage.tsx frontend/src/features/shared/api.ts frontend/src/app/globals.css frontend/src/features/opportunities/OpportunityPage.test.tsx
git commit -m "feat: populate operational workspaces"
```

### Task 6: Full Verification and Browser Acceptance

**Files:**
- Modify: `README.md`
- Modify: `docs/IMPLEMENTATION_PLAN.md`

**Interfaces:**
- Consumes: completed backend and frontend workflows.
- Produces: reproducible local startup, login, refresh, and verification instructions.

- [ ] **Step 1: Run the complete backend suite**

Run: `python -m pytest -q`
Expected: all backend tests pass with zero failures.

- [ ] **Step 2: Run all frontend quality gates**

Run: `npm test`
Expected: all frontend tests pass with zero failures.

Run: `npm run lint`
Expected: exit code 0.

Run: `npm run build`
Expected: production build succeeds.

- [ ] **Step 3: Exercise the real browser workflow**

Start backend and frontend, open `http://localhost:3000`, save a brand profile, start refresh, observe stage changes, verify terminal feedback, open a real opportunity when available, and navigate through all five modules. Confirm the white/forest-green layout remains responsive and no fake records appear.

- [ ] **Step 4: Document exact operator steps and current external prerequisites**

Update README with the pinned crawler login command, backend/frontend startup commands, AI environment requirements, data directory, and recovery guidance for expired login or partial refresh.

- [ ] **Step 5: Commit**

```bash
git add README.md docs/IMPLEMENTATION_PLAN.md
git commit -m "docs: add live workflow operating guide"
```
