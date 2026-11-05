# Expansion plan

One step at a time. Each step lists its assessment, decisions, plan, and
(after it is merged) an "As built" note. Rules: docs/project_context.md.

---

## Step 1: Live ingestion

Branch: `exp/01-live-ingestion` (from `expansion` at `d721af3`).
Scope (from the project_context.md roadmap): single-record POST, simulator,
dashboard polling. Nothing beyond that.

Status: COMPLETE (M1, M2, M3 merged into expansion). Plan approved by
the student on 2026-10-31, with NQ-9 kept. BQ-1 approved (D-1).

### Step 1: existing repository assessment

Inspected on 2026-10-31 from the code, tests and git log (15 commits on
`expansion`), not from memory.

**What exists**

| Area | File | Facts relevant to this step |
| :--- | :--- | :--- |
| Routes | backend/app/routes.py | 5 endpoints under `/api/v1`: `POST /ingest/csv`, `GET /current-state`, `GET /forecast`, `GET /anomalies`, `GET /recommendations`. Plus `GET /health` in main.py. |
| Ingestion | backend/app/ingestion.py | `parse_and_validate_csv` (pandas, then `OperationalRowSchema` per row, 422 on any bad row) and `ingest_operational_csv` (idempotent upsert keyed by UTC timestamp; loads all rows into a dict, then inserts or updates; one commit). Naive timestamps are treated as UTC (`pd.to_datetime(..., utc=True)`). |
| Schemas | backend/app/schemas.py | `OperationalRowSchema` (7 fields, all ints `ge=0`, ICU `0..100`). `IngestionResponse` has a required `filename`, so it does not fit a JSON record. Response schemas coerce naive timestamps to UTC. |
| Database | backend/app/database.py | One table `operational_metrics`, `timestamp` is `unique=True`, `DateTime(timezone=True)`. `create_all` at startup. Default SQLite engine settings. |
| Layers | state.py, forecast.py, anomaly.py, optimizer.py | All read the latest row by `ORDER BY timestamp DESC`. Each endpoint computes on request; nothing is cached, so a new row is visible on the next GET. `optimizer.py` calls `get_ed_forecast`, so a forecast error also fails `/recommendations`. |
| Forecast lags | backend/app/forecast.py | Order of checks: model file exists, then at least 25 rows. Then takes the latest 25 rows and uses `rows[1]` and `rows[24]` as t-1 and t-24, i.e. by position, not by timestamp. |
| Scripts | backend/scripts/ | `generate_synthetic_data.py` (consecutive hours, `start + i hours`), `train_forecaster.py`. No simulator. |
| Tests | backend/tests/ | 16 tests (test_api 1, test_ingest 5, test_layers 10). `client` fixture overrides `get_db` with an in-memory StaticPool session. Every existing test that reaches the forecast uses consecutive hours. |
| Frontend | frontend/src/app/page.tsx | `refreshDashboard()` fetches the 4 GET endpoints once on mount and after a CSV upload. It sets every loading flag to true, and on error sets that card's data to null. No polling. |
| Frontend | frontend/src/components/Navbar.tsx | Shows "Latest data" (`formatUtcDateTime(latestTimestamp)`) and the upload button. |
| Frontend API | frontend/src/lib/api.ts | `fetch` with `cache: "no-store"`. HTTP errors become `Error` with `status`; a network failure throws a `TypeError` without `status`. |
| Dependencies | backend/requirements.txt | Python stdlib `urllib` is enough for the simulator; no new package needed. |

**Baseline test run** (fresh venv): first run 6 failed / 10 passed because
`backend/models/ed_forecaster.joblib` is gitignored and was not present.
After the README step `python backend/scripts/train_forecaster.py`:
16 passed, 1 warning (known Starlette/httpx warning). Recorded in
docs/loop_log.md.

**What this step touches**: schemas.py, ingestion.py, routes.py
(additions only), forecast.py (gap check only, NQ-9), a new simulator
script, new tests, frontend page.tsx and Navbar.tsx, README.md.

**Where plan.md and the code disagree (reported, not fixed)**

1. plan.md §2.2 "Conflict 2" narrows ingestion to CSV upload only. This
   step adds a JSON single-record endpoint. Resolved by decision D-1
   (approved by the student); plan.md itself is not edited.
2. plan.md REQ-001 says CSV rows are "appended" and must be "positive
   integers". The code upserts (matches OPQ-002 and §11.1) and accepts 0
   (`ge=0`). REQ-001 text is stale. The new endpoint follows the code
   (upsert, `ge=0`). Not changed.
3. plan.md REQ-005 / §7.1 describe t-1 and t-24 lags. The code takes them
   by row position, which is only correct when the rows are consecutive
   hours. This step does not change how lags are chosen; NQ-9 adds a check
   that refuses to forecast when the latest 25 rows are not consecutive.
4. project_context.md says `v1-demo` is the tag of the viva-ready version.
   `git tag` shows no tags at all in this clone. Not changed.
5. The `client` test fixture enters `TestClient(app)`, whose lifespan calls
   `init_db()` on the real `DATABASE_URL`. This creates an empty
   `hospital_operations.db` (gitignored) when tests run. Pre-existing; no
   data is written to it. Not changed.

### Step 1: decisions

**D-1: Live single-record ingestion is allowed (supersedes plan.md §2.2
"Conflict 2" for ingestion)**
- What changed: plan.md §2.2 narrowed ingestion to CSV multipart upload
  only (`POST /api/v1/ingest/csv`). From this step, the system also
  accepts one hourly record as JSON at `POST /api/v1/ingest/record`.
- Why: the expansion roadmap's step 1 is live ingestion, and the final
  vision is a simulated real-time feed. A live feed sends one record at a
  time, which the CSV-only path cannot do.
- Approved by: the student (project owner), 2026-10-31, as BQ-1.
- Scope of the reversal: for ingestion only, this decision supersedes
  plan.md §2.2. plan.md is not edited. CSV upload keeps working exactly as
  before: same route, same validation, same upsert, same response; its
  code and tests are not changed.

### Step 1: plan

#### Requirements

Highest existing ID in plan.md is REQ-011, so this step starts at REQ-012.

| ID | Requirement | Acceptance criteria | Test |
| :--- | :--- | :--- | :--- |
| REQ-012 | Single-record JSON ingestion | `POST /api/v1/ingest/record` accepts one hourly record as JSON (same 7 fields and ranges as `OperationalRowSchema`). New timestamp -> row inserted, `action="inserted"`, HTTP 200. Existing instant -> row updated, `action="updated"`, row count unchanged. Invalid or missing field -> 422, nothing written. "Latest" is the maximum timestamp (NQ-8), so an older record does not change `GET /current-state`. | backend/tests/test_live_ingest.py: `test_post_record_inserts_and_updates_current_state`, `test_post_record_duplicate_timestamp_updates`, `test_post_record_rejects_invalid_and_missing_fields`, `test_post_record_out_of_order_does_not_change_current_state`, `test_post_record_naive_timestamp_treated_as_utc`, `test_post_record_other_offset_matches_existing_row` (a `+05:30` timestamp for an existing UTC instant updates that row, row count unchanged) |
| REQ-013 | Live feed simulator script | `backend/scripts/simulate_live_feed.py` (NQ-12): before each send, reads the latest timestamp from `GET /current-state`, builds a record with `timestamp = latest + 1 hour` and the values of the source CSV row with the same hour-of-week, and POSTs it to `/api/v1/ingest/record`. Repeats every `--interval` seconds for `--count` records. Exits with a clear message and code 1 if the backend is unreachable, the database is empty (404), or a POST fails. Stdlib only. | backend/tests/test_simulator.py: `test_build_next_record_is_next_hour_same_hour_of_week`, `test_build_next_record_passes_schema`, `test_simulated_record_posts_and_becomes_current` (posts through the `client` fixture, no network), `test_simulator_exits_cleanly_when_backend_unreachable` (points at a closed localhost port; asserts exit code 1 and the message) |
| REQ-014 | Dashboard polling with refresh status | Every 10 s the dashboard re-fetches the 4 GET endpoints without loading skeletons (skeletons only on first load and after a CSV upload). The navbar shows "Latest data" (max timestamp) and "Last refreshed" (time of the last successful poll). If a poll cannot reach the backend, cards keep their last data, nothing crashes or blanks, and a short "Live updates paused" message (icon + text) shows until a poll succeeds (NQ-7). Polling stops on unmount. | Manual (no frontend tests, per project_context.md): run backend, frontend and simulator, watch both times advance; stop the backend, see the paused message with cards still filled; restart, see it clear. Plus `npm run lint` and `npm run build` pass. |
| REQ-015 | Forecast gap check (NQ-9) | After the existing "model exists" and "at least 25 rows" checks, `get_ed_forecast` checks that each of the latest 25 rows is exactly 1 hour after the previous one. If not: HTTP 400, detail `Data has a gap in the last 25 hours; upload or send the missing hours`. Applies to CSV and live data alike. `/recommendations` returns the same 400 because it calls the forecast. Consecutive data -> behaviour unchanged. | backend/tests/test_forecast_gap.py: `test_forecast_gap_returns_400` (CSV upload with one missing hour inside the latest 25 -> `GET /forecast` 400 with the message), `test_forecast_consecutive_hours_ok` (25 consecutive hours -> 200) |

Concurrency check for NQ-11 is a verification step in M3, not a
requirement.

#### Interfaces and data contracts (defined before implementation)

`POST /api/v1/ingest/record`, tag `Ingestion`, no authentication (NQ-10).

Request body: `OperationalRowSchema` unchanged.

```json
{
  "timestamp": "2026-10-29T14:00:00Z",
  "ed_arrivals": 57,
  "ed_patients": 46,
  "available_beds": 42,
  "icu_occupancy_pct": 87.0,
  "nurses_available": 10,
  "doctors_available": 4
}
```

Response 200, new schema `RecordIngestionResponse` in schemas.py:

```json
{ "status": "success", "action": "inserted", "timestamp": "2026-10-29T14:00:00Z" }
```

- `status`: always `"success"` on 200.
- `action`: `"inserted"` or `"updated"`.
- `timestamp`: the stored instant in UTC (naive input is treated as UTC,
  offset input is converted to UTC, same as the CSV path).

Errors: 422 from FastAPI/Pydantic validation. No other new error codes.

Backend function (ingestion.py):
`ingest_single_record(record: OperationalRowSchema, db: Session) -> RecordIngestionResponse`.
Matches an existing row by UTC instant (same normalisation as the CSV
path), then updates or inserts, then commits.

Forecast gap check (forecast.py): after `if len(rows) < 25`, compare each
pair of neighbouring rows in `rows`; if any difference is not exactly
1 hour, raise `HTTPException(400, "Data has a gap in the last 25 hours;
upload or send the missing hours")`. Nothing else in the function changes.

Simulator (backend/scripts/simulate_live_feed.py):

- CLI: `--api-base` (default `http://localhost:8000`), `--source`
  (default `hospital_operations_synthetic.csv`), `--interval` seconds
  (default 5), `--count` records (default 24).
- Pure function: `build_next_record(latest_ts: datetime, source_rows:
  list[dict]) -> dict` returns a JSON-ready dict with the 7 fields.
- Hour-of-week of `latest_ts + 1h` is `weekday() * 24 + hour`; the first
  source row with the same hour-of-week supplies the 6 values.
- Loop per send: GET current-state -> build -> POST -> print one line
  (timestamp, action) -> sleep `--interval`.

Frontend:

- page.tsx: `refreshDashboard(showLoading: boolean)`. Initial load and
  post-upload use `true` (as today). A `useEffect` starts
  `setInterval(() => refreshDashboard(false), POLL_INTERVAL_MS)` and
  clears it on unmount. `POLL_INTERVAL_MS = 10000`.
- On a poll (`showLoading=false`):
  - a request that gets an HTTP response updates that card as today
    (data on 200, the card's error message on an HTTP error such as the
    NQ-9 400);
  - a request that cannot reach the backend (no HTTP status) leaves that
    card's data and error unchanged and sets `livePaused = true`.
  - If all 4 requests got an HTTP response, `livePaused = false` and
    `lastRefreshedAt = new Date()`.
- Navbar.tsx: two new optional props, `lastRefreshedAt?: Date | null` and
  `livePaused?: boolean`. Shows "Last refreshed: HH:MM:SS" (browser local
  time) next to "Latest data", and when paused an icon + text "Live updates
  paused. Showing last data." Matches the existing look (no new colours
  beyond the existing palette, sentence case, icon plus text).
- No new API function; the dashboard never calls the POST endpoint.

#### Failure modes

| Input | Behaviour |
| :--- | :--- |
| Bad value (negative, ICU > 100, wrong type, bad timestamp) | 422 with Pydantic detail; nothing written. |
| Missing field | 422; nothing written. |
| Extra unknown field | Ignored (NQ-3). |
| Duplicate timestamp | Existing row updated; `action="updated"`; row count unchanged (NQ-1). |
| Same instant in another offset (e.g. `+05:30`) | Normalised to UTC, matches the existing row, updates it; row count unchanged. |
| Out-of-order or late record (older than latest) | Accepted and upserted by timestamp (NQ-8). "Latest" is the maximum timestamp, never the last arrival, so `/current-state`, `/anomalies` and the forecast's latest row do not change. If the late record fills a missing hour, the gap check (NQ-9) may pass again. If it lands inside the latest 25 rows off the hourly grid, `/forecast` and `/recommendations` return the NQ-9 400. |
| Gap in the hourly sequence | Stored. While the latest 25 rows are not consecutive hours, `/forecast` and `/recommendations` return 400 "Data has a gap in the last 25 hours; upload or send the missing hours" (NQ-9). `/current-state` and `/anomalies` still work. Applies to CSV uploads too. Clears when the missing hours are sent or 25 consecutive hours follow the gap. The simulator never creates gaps. |
| Timestamp not on the hour | Accepted (NQ-2); see the out-of-order row for its effect on the forecast. |
| Simulator: backend unreachable | Prints "Cannot reach the backend at <api-base>: <reason>" and exits with code 1 (NQ-12). |
| Simulator: database empty | `GET /current-state` 404 -> prints "No data in the database. Upload a CSV first." and exits with code 1. |
| Simulator: POST returns non-200 | Prints status and detail, exits with code 1. |
| Simulator: source CSV missing or no row for that hour-of-week | Clear message, exit code 1. |
| Dashboard: backend unreachable during a poll | Cards keep last data, no crash, "Live updates paused" shows; "Last refreshed" stops advancing; next successful poll clears it (NQ-7). |
| Dashboard: HTTP error during a poll (e.g. NQ-9 400) | That card shows its error, as today; other cards unaffected. |
| Dashboard: poll while previous poll in flight | Accepted; each request sets its own state. Unlikely at 10 s. |
| SQLite: simulator writes while dashboard reads | Current settings kept (NQ-11). Checked in M3; any "database is locked" error -> STOP and ask. |
| Anyone on the network calls the POST | No authentication (NQ-10). Demo runs on localhost only. |

#### Milestones

**M1: Single-record endpoint and forecast gap check (REQ-012, REQ-015)**
- Tasks: add `RecordIngestionResponse` to schemas.py; add
  `ingest_single_record` to ingestion.py; add the route to routes.py; add
  backend/tests/test_live_ingest.py; add the gap check to forecast.py; add
  backend/tests/test_forecast_gap.py.
- Done when: the 8 new tests (6 + 2) and all 16 existing tests pass,
  unedited; `/docs` lists `POST /api/v1/ingest/record`; CSV upload of
  hospital_operations_synthetic.csv still returns 200 with the same
  response shape.

**M2: Simulator (REQ-013)**
- Tasks: add backend/scripts/simulate_live_feed.py; add
  backend/tests/test_simulator.py; add a "Live feed simulator" section to
  README.md (PowerShell command, new endpoint, "unauthenticated, localhost
  only").
- Done when: the 4 new tests and all previous tests pass; a manual run
  against a local backend loaded with the synthetic CSV posts `--count 3`
  records and `GET /current-state` advances by 3 hours; a run with the
  backend stopped exits with code 1 and the clear message.

**M3: Dashboard polling (REQ-014) and concurrency check (NQ-11)**
- Tasks: change page.tsx and Navbar.tsx as described.
- Verification: start backend (logging to a file), frontend, and the
  simulator with `--interval 1 --count 60` while the dashboard is open and
  polling. Then search the backend log and simulator output for
  `database is locked`. Also stop the backend once to check the paused
  message, then restart.
- Done when: `npm run lint` and `npm run build` pass; the full backend
  suite passes; the manual run shows both times advancing, the paused
  message without blank cards, and zero `database is locked` lines. If any
  appear: STOP, write docs/BLOCKED.md, ask (NQ-11).

#### Files

Create:
- backend/tests/test_live_ingest.py
- backend/tests/test_forecast_gap.py
- backend/tests/test_simulator.py
- backend/scripts/simulate_live_feed.py

Change:
- backend/app/schemas.py: add `RecordIngestionResponse` (addition only).
- backend/app/ingestion.py: add `ingest_single_record` (addition only).
- backend/app/routes.py: add one route (addition only).
- backend/app/forecast.py: add only the NQ-9 gap check (one HTTP 400).
- frontend/src/app/page.tsx: `showLoading` parameter, polling effect,
  `livePaused` and `lastRefreshedAt` state.
- frontend/src/components/Navbar.tsx: "Last refreshed" and the paused
  message (two optional props).
- README.md: simulator section, new endpoint, localhost-only note.
- expansion_plan.md: status and "As built".
- docs/loop_log.md: run log.

Must not change:
- plan.md, docs/project_context.md.
- Any existing test file in backend/tests.
- `POST /api/v1/ingest/csv`: route, validation, upsert, response.
- `OperationalRowSchema`, the database schema, the model and training.
- state.py, anomaly.py, optimizer.py, database.py, config.py, main.py.
- forecast.py apart from the NQ-9 check (lag choice, features, model
  loading, response shape stay the same).
- Other frontend files (components, api.ts, types.ts, styles).
- hospital_operations.db, hospital_operations_synthetic.csv.
- requirements.txt and package.json (no new dependencies).

#### Open questions and choices

BLOCKING
- BQ-1: APPROVED by the student on 2026-10-31. Recorded as D-1.
- None open.

NON-BLOCKING (all PROVISIONAL, reversible)
- NQ-1 PROVISIONAL (accepted): duplicate timestamp updates the row
  (upsert) rather than returning 409. Why: matches the CSV path and
  OPQ-002, so both paths behave the same.
- NQ-2 PROVISIONAL (accepted): timestamps are not forced onto the hour.
  Why: the CSV path does not enforce it either; enforcing it only here
  would make the two paths disagree.
- NQ-3 PROVISIONAL (accepted): unknown extra JSON fields are ignored. Why:
  Pydantic default, no schema change, and `OperationalRowSchema` is shared
  with the CSV path.
- NQ-4 PROVISIONAL (accepted): the simulator replays the CSV row with the
  same hour-of-week instead of random values. Why: realistic daily and
  weekly pattern, deterministic, explainable in one sentence.
- NQ-5 PROVISIONAL (accepted): poll every 10 s; simulator default interval
  5 s. Why: changes are visible during a demo and the load on local SQLite
  stays light.
- NQ-6 PROVISIONAL (accepted): polling instead of WebSockets/SSE. Why: the
  roadmap says polling, and it needs no new server component.
- NQ-7 PROVISIONAL (amended by the student): the dashboard shows the
  latest data timestamp and the time of the last successful refresh. If a
  poll fails, it keeps the last data and shows a short "Live updates
  paused" message, with no crash and no blank cards. Why: a viewer must be
  able to tell live data from stale data. Implementation choice (also
  PROVISIONAL): "poll fails" means the backend could not be reached (no
  HTTP response). An HTTP error such as the NQ-9 400 is a real answer and
  is shown on that card as today, because hiding it would show a stale
  forecast as if it were current.
- NQ-8 PROVISIONAL: late or out-of-order records are accepted and upserted
  by timestamp. "Latest" always means the maximum timestamp, never the
  last arrival. Why: real feeds deliver late data; ordering by timestamp is
  what every layer already does.
- NQ-9 PROVISIONAL: the forecast checks that the latest 25 rows are
  consecutive hours; if not, HTTP 400 "Data has a gap in the last 25
  hours; upload or send the missing hours". Applies to CSV data too. Only
  forecast.py changes, and only by adding this check. Why: the model's
  t-1 and t-24 lags are taken by row position, so a gap would silently
  feed it wrong values; a clear 400 follows the no-fallback rule.
  Existing tests reaching the forecast all use consecutive hours (checked
  by reading test_layers.py and test_api.py; to be confirmed by running
  them in M1). The new check runs after the existing two checks, so the
  existing "Model not trained" and "Insufficient lag data" tests keep
  their messages.
- NQ-10 PROVISIONAL: no authentication in this step, consistent with
  project_context.md. `POST /api/v1/ingest/record` is unauthenticated, so
  anyone who can reach the backend can write data; the demo runs on
  localhost only. Why: authentication is outside this step; hardening
  stays on the roadmap (step 8).
- NQ-11 PROVISIONAL: SQLite with one writer (simulator) and readers
  (dashboard) keeps the current engine settings. Why: changing them (WAL
  mode, timeouts, another database) could reverse recorded decisions. M3
  verifies it; any "database is locked" error -> STOP and ask.
- NQ-12 PROVISIONAL: simulator timestamps continue the series, one hour
  after the latest record in the database for each send, with the values
  of the same hour-of-week CSV row. It exits with a clear message if the
  backend is unreachable. Why: reading the latest timestamp before every
  send keeps the series consecutive even if other data arrives, so the
  NQ-9 check passes.

**Scope note on NQ-9 (as asked):** it is slightly outside the literal
scope ("single-record POST, simulator, polling") because it changes
Layer 2 behaviour, also for CSV data. I recommend keeping it in this step:
live ingestion is what makes gaps likely, the change is one check with no
new data or settings, and without it the forecast would silently use wrong
lags. If you prefer the literal scope, drop REQ-015 and its 2 tests and
leave the gap risk documented under disagreement 3.

### Step 1: As built

Built as planned; all three milestones merged into `expansion` (tags
merged-01-m1, merged-01-m2, merged-01-m3).

- **M1 (REQ-012, REQ-015):** `POST /api/v1/ingest/record` (`RecordIngestionResponse`,
  `ingest_single_record`, upsert by UTC instant, 422 on bad input) and the
  forecast gap check (400 "Data has a gap in the last 25 hours; upload or send
  the missing hours"). 8 new tests.
- **M2 (REQ-013):** `backend/scripts/simulate_live_feed.py` (stdlib only),
  README section "7. Live feed simulator". 4 new tests.
- **M3 (REQ-014):** `page.tsx` polls every 10 s with no loading skeletons;
  `Navbar.tsx` shows "Last refreshed" and "Live updates paused. Showing last
  data." when the backend cannot be reached.
- Tests: 16 existing (unedited) + 12 new = 28 passed. No new dependencies.
- NQ-11 check: 200 simulator writes at 0.1 s with 3 concurrent pollers
  (1036 reads, all HTTP 200): "database is locked" 0 times. SQLite settings
  unchanged.

**Deviations from the plan**
1. `test_simulated_record_posts_and_becomes_current` uses 8 days of
   generated data, not 3 (3 days ends Saturday 23:00 and Sunday 00:00 has no
   matching hour-of-week row).
2. `frontend/src/components/ForecastCard.tsx` was changed by two lines (a
   pre-existing `no-explicit-any` lint error, `null as any` replaced by a
   nullable number type), approved by the student, so `npm run lint` passes.
3. `page.tsx`: the unused `isRefreshing` state and unused imports were
   removed, and the first load runs through `setTimeout(..., 0)` because the
   lint rule rejects `setState` called directly in an effect.
4. The student's own commit 3d5d5cb (docs/project_context.md rule wording) is
   on this branch, so merge gate check 4 showed that diff; accepted by the
   student. Tag cp-01-m3 predates the lint fix; the final M3 checkpoint is
   cp-01-m3b (tags are never moved).
5. The "Last refreshed" chip uses `hidden sm:flex` like "Latest data", so
   below 640px only the paused message is visible. Layouts below 640px were
   not checked.
6. The unedited "Must not change" list was followed otherwise; plan.md and
   all existing tests are untouched.
