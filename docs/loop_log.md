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
