# Loop log

## Step 1: Live ingestion (exp/01-live-ingestion)

### 2026-10-31: setup and baseline

- Branch: `exp/01-live-ingestion` created from `expansion` (`d721af3`).
  Working tree was clean.
- Environment: `.venv` (Python 3.12.10) populated with
  `.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt`.
  No new dependencies (only the existing pinned list).
- Command: `.\.venv\Scripts\python.exe -m pytest backend/tests -q`
  - Result: 6 failed, 10 passed. All 6 failures were
    `400: Model not trained. Run train_forecaster.py first`
    (`backend/models/ed_forecaster.joblib` is gitignored and absent in this
    checkout).
- Command: `.\.venv\Scripts\python.exe backend/scripts/train_forecaster.py`
  (README setup step). Output: Test MAE 3.09, RMSE 3.93, model saved.
- Command: `.\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider`
  - **Baseline: 16 passed, 1 warning** (known Starlette/httpx warning).
- Files changed: expansion_plan.md (created), docs/loop_log.md (created),
  docs/BLOCKED.md (created, awaiting plan approval).
- Stopped after Phase 2: plan approval not given and one blocking question
  (BQ-1). See docs/BLOCKED.md.

### 2026-10-31: plan revision

- Student approved BQ-1. Recorded as decision D-1 (live ingestion
  supersedes plan.md §2.2 for ingestion; CSV upload unchanged).
- Student accepted NQ-1 to NQ-6, amended NQ-7, and added NQ-8 to NQ-12.
  Added REQ-015 (forecast gap check), the `+05:30` offset test, the
  simulator "backend unreachable" test, and the M3 concurrency check.
- Files changed: expansion_plan.md (rewritten Step 1 section),
  docs/loop_log.md, docs/BLOCKED.md (still present, uncommitted).
- No code written. Stopped for final plan approval.

### 2026-10-31: plan approved, Milestone 1 (REQ-012, REQ-015)

- Student approved the plan and kept NQ-9. docs/BLOCKED.md deleted.
- Code written by a Sonnet 5.5 subagent, diff reviewed by the main agent.
- Tasks done: RecordIngestionResponse (schemas.py), ingest_single_record
  (ingestion.py), POST /api/v1/ingest/record (routes.py), gap check in
  get_ed_forecast (forecast.py), 8 new tests.
- Command: .\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider
  - Result: **24 passed, 1 warning** (16 existing unedited + 8 new).
- Files changed: backend/app/schemas.py, ingestion.py, routes.py,
  forecast.py; new backend/tests/test_live_ingest.py,
  backend/tests/test_forecast_gap.py; expansion_plan.md (status).
- Dependencies added: none.
- Explanation, single-record endpoint: It accepts one hourly record as
  JSON, checks it with the same rules as a CSV row, and stores it. If a
  row with the same UTC time exists it is updated, otherwise a new row is
  added.
- Explanation, forecast gap check: Before forecasting it checks that the
  latest 25 rows are exactly one hour apart. If not, it returns a clear
  400 error, because the model's 1-hour and 24-hour lags would otherwise
  be wrong.

### 2026-10-31: Milestone 2 (REQ-013)

- Code written by a Sonnet 5.5 subagent, diff reviewed by the main agent.
- Tasks done: backend/scripts/simulate_live_feed.py, 4 new tests in
  backend/tests/test_simulator.py, README section "7. Live feed simulator".
- Command: .\.venv\Scripts\python.exe -m pytest backend/tests -q -p no:cacheprovider
  - Result: **28 passed, 1 warning** (24 earlier + 4 new).
- Manual run (temporary SQLite file, deleted afterwards; hospital_operations.db untouched):
  uploaded hospital_operations_synthetic.csv (1440 rows, latest 2026-11-29T23:00:00Z);
  simulator --count 3 --interval 1 posted 2026-11-30T00:00:00Z, 01:00:00Z and
  02:00:00Z (all inserted); current-state then showed 2026-11-30T02:00:00Z
  (+3 hours). With the backend stopped the simulator printed
  "Cannot reach the backend at http://localhost:8000: ..." and exited with code 1.
- Deviation from plan: test_simulated_record_posts_and_becomes_current uses
  generate_synthetic_data(days=8) instead of days=3, because 3 days starts on
  a Thursday and ends Saturday 23:00, and Sunday 00:00 has no matching row.
- Files changed: backend/scripts/simulate_live_feed.py (new),
  backend/tests/test_simulator.py (new), README.md, docs/loop_log.md.
- Dependencies added: none (standard library only).
- Explanation, simulator: It asks the backend for the latest record time,
  then builds a record for the next hour using the values from the same
  weekday and hour in the sample CSV. It sends that record to the live
  endpoint every few seconds and stops with a clear message if the backend
  is down or empty.

### 2026-10-31: Milestone 3 (REQ-014, NQ-7, NQ-11)

- Student made and committed an edit to docs/project_context.md (commit
  3d5d5cb on this branch, "Prefer the simplest approach..." rule). BLOCKED.md
  from the earlier stop was deleted.
- Code written by a Sonnet 5.5 subagent, diff reviewed by the main agent.
- Tasks done: page.tsx (showLoading parameter, 10 s polling, livePaused and
  lastRefreshedAt state), Navbar.tsx ("Last refreshed" chip and the
  "Live updates paused. Showing last data." message). No other frontend file.
- Backend suite: 28 passed, 1 warning.
- npm run build: exit 0. npm run lint: exit 1, one error that is NOT in a file
  changed here: ForecastCard.tsx:67:23 no-explicit-any. The same error exists
  without this milestone's changes (baseline lint also had 2 errors and 3
  warnings in page.tsx that this milestone removed).
- NQ-11 check (temporary SQLite file, port 8011): simulator 200 writes at
  0.1 s intervals while 3 threads polled the 4 GET endpoints. Result: simulator
  exit 0, 200 lines, 1036 reads all HTTP 200 (259 per endpoint, no 400/404),
  "database is locked" occurred 0 times.
- Browser check (integrated browser, temp DB): Last refreshed advanced and
  Latest data moved after the simulator posted; stopping the backend showed
  the paused message with cards still filled; restarting cleared it. The
  below-640px layout was not checked.
- Files changed: frontend/src/app/page.tsx, frontend/src/components/Navbar.tsx,
  docs/loop_log.md. Dependencies added: none (npm install used the existing
  lockfile).
- Explanation, dashboard polling: Every 10 seconds the page quietly asks the
  backend for the four layer results again and updates the cards without
  showing loading placeholders. The navbar shows when the last refresh worked,
  and if the backend cannot be reached it keeps the old data and says live
  updates are paused.

### 2026-10-31: Milestone 3 lint fix (student approved)

- Student approved a one-line type fix in frontend/src/components/ForecastCard.tsx
  (pre-existing no-explicit-any error): `observed: pt.arrivals as number | null`
  and `observed: null` replace `null as any`. Behaviour unchanged.
- npm run lint: exit 0. npm run build: exit 0 (Next.js, 4 static pages).
- Tag cp-01-m3 already points at f7395c9 (before the fix); tags are never
  moved, so the final M3 checkpoint is tagged cp-01-m3b.
- Files changed: frontend/src/components/ForecastCard.tsx, docs/loop_log.md.
