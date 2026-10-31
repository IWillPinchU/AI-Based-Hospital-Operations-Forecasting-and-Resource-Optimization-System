# Expansion plan

One step at a time. Each step lists its assessment, plan, and (after it is
merged) an "As built" note. Rules: docs/project_context.md.

---

## Step 1: Live ingestion

Branch: `exp/01-live-ingestion` (from `expansion` at `d721af3`).
Scope (from the project_context.md roadmap): single-record POST, simulator,
dashboard polling. Nothing beyond that.

Status: PLANNED, waiting for approval (see docs/BLOCKED.md).

### Step 1: existing repository assessment

Inspected on 2026-10-31 from the code, tests and git log (15 commits on
`expansion`), not from memory.

**What exists**

| Area | File | Facts relevant to this step |
| :--- | :--- | :--- |
| Routes | backend/app/routes.py | 5 endpoints under `/api/v1`: `POST /ingest/csv`, `GET /current-state`, `GET /forecast`, `GET /anomalies`, `GET /recommendations`. Plus `GET /health` in main.py. |
| Ingestion | backend/app/ingestion.py | `parse_and_validate_csv` (pandas, then `OperationalRowSchema` per row, 422 on any bad row) and `ingest_operational_csv` (idempotent upsert keyed by UTC timestamp; loads all rows into a dict, then inserts or updates; one commit). Naive timestamps are treated as UTC (`pd.to_datetime(..., utc=True)`). |
| Schemas | backend/app/schemas.py | `OperationalRowSchema` (7 fields, all ints `ge=0`, ICU `0..100`). `IngestionResponse` has a required `filename`, so it does not fit a JSON record. Response schemas coerce naive timestamps to UTC. |
| Database | backend/app/database.py | One table `operational_metrics`, `timestamp` is `unique=True`, `DateTime(timezone=True)`. `create_all` at startup. |
| Layers | state.py, forecast.py, anomaly.py, optimizer.py | All read the latest row by `ORDER BY timestamp DESC`. Each endpoint computes on request; nothing is cached, so a new row is visible on the next GET. |
| Forecast lags | backend/app/forecast.py | Takes the latest 25 rows and uses `rows[1]` and `rows[24]` as t-1 and t-24, i.e. by position, not by timestamp. |
| Scripts | backend/scripts/ | `generate_synthetic_data.py`, `train_forecaster.py`. No simulator. |
| Tests | backend/tests/ | 16 tests (test_api 1, test_ingest 5, test_layers 10). `client` fixture overrides `get_db` with an in-memory StaticPool session. |
| Frontend | frontend/src/app/page.tsx | `refreshDashboard()` fetches the 4 GET endpoints once on mount and after a CSV upload. It sets every loading flag to true, so calling it repeatedly would flash skeletons. No polling. |
| Frontend API | frontend/src/lib/api.ts | `fetch` with `cache: "no-store"`, base URL from `NEXT_PUBLIC_API_BASE_URL`. |
| Dependencies | backend/requirements.txt | Python stdlib `urllib` is enough for the simulator; no new package needed. |

**Baseline test run** (fresh venv): first run 6 failed / 10 passed because
`backend/models/ed_forecaster.joblib` is gitignored and was not present.
After the README step `python backend/scripts/train_forecaster.py`:
16 passed, 1 warning (known Starlette/httpx warning). Recorded in
docs/loop_log.md.

**What this step touches**: routes.py, ingestion.py, schemas.py (additions
only), a new script, new tests, frontend page.tsx / api.ts / types.ts /
Navbar.tsx, README.md (how to run the simulator).

**Where plan.md and the code disagree (reported, not fixed)**

1. plan.md §2.2 "Conflict 2" narrows ingestion to CSV upload only. This
   step adds a JSON single-record endpoint. The project_context.md roadmap
   lists it, but it reverses a plan.md decision, so this plan needs
   explicit approval. Affects this step.
2. plan.md REQ-001 says CSV rows are "appended" and must be "positive
   integers". The code upserts (matches OPQ-002 and §11.1) and accepts 0
   (`ge=0`). The code is internally consistent with OPQ-002; REQ-001 text
   is stale. Does not block this step; the new endpoint follows the code
   (upsert, `ge=0`).
3. plan.md REQ-005 / §7.1 describe t-1 and t-24 lags. The code takes them
   by row position. That is only correct when rows are consecutive hours
   with no gaps. CSV uploads of the synthetic data satisfy this; live
   single records may not (gaps, out-of-order). Not fixed in this step
   (out of scope); the simulator is designed to always send the next
   consecutive hour so the demo stays correct. Affects failure modes below.
4. project_context.md says `v1-demo` is the tag of the viva-ready version.
   `git tag` shows no tags at all in this clone. Not changed by this step.
5. The `client` test fixture enters `TestClient(app)`, whose lifespan calls
   `init_db()` on the real `DATABASE_URL`. This creates an empty
   `hospital_operations.db` (gitignored) in the working directory when
   tests run. Pre-existing; no data is written to it. Not changed.

### Step 1: plan

#### Requirements

Highest existing ID in plan.md is REQ-011, so this step starts at REQ-012.

| ID | Requirement | Acceptance criteria | Test |
| :--- | :--- | :--- | :--- |
| REQ-012 | Single-record JSON ingestion | `POST /api/v1/ingest/record` accepts one hourly record as JSON (same 7 fields and ranges as `OperationalRowSchema`). New timestamp -> row inserted, response `action="inserted"`, HTTP 200. Existing timestamp (same UTC instant) -> row updated, `action="updated"`, row count unchanged. Invalid or missing field -> HTTP 422, nothing written. After a successful POST, `GET /current-state` returns the new record if it is the latest. | backend/tests/test_live_ingest.py: `test_post_record_inserts_and_updates_current_state`, `test_post_record_duplicate_timestamp_updates`, `test_post_record_rejects_invalid_and_missing_fields`, `test_post_record_out_of_order_does_not_change_current_state`, `test_post_record_naive_timestamp_treated_as_utc` |
| REQ-013 | Live feed simulator script | `backend/scripts/simulate_live_feed.py` reads the latest timestamp from `GET /current-state`, builds the next hour's record by copying the source CSV row with the same hour-of-week and setting `timestamp = latest + 1 hour`, and POSTs it to `/api/v1/ingest/record`. Repeats every `--interval` seconds for `--count` records. Stops with a clear message and non-zero exit if the database is empty (404) or the API is unreachable. Stdlib only (`csv`, `json`, `urllib`, `argparse`). | backend/tests/test_simulator.py: `test_build_next_record_is_next_hour_same_hour_of_week`, `test_build_next_record_passes_schema`, `test_simulated_record_posts_and_becomes_current` (posts the built record through the `client` fixture, no network) |
| REQ-014 | Dashboard polling | The dashboard re-fetches the 4 GET endpoints every 10 seconds without showing loading skeletons on each poll (skeletons only on first load and after a CSV upload). Navbar "Latest data" updates when the simulator adds a row. Polling stops when the page unmounts. | Manual (no frontend tests, per project_context.md): run backend, frontend and simulator; observe "Latest data" advance. Plus `npm run lint` and `npm run build` pass. |

#### Interfaces and data contracts (defined before implementation)

`POST /api/v1/ingest/record`, tag `Ingestion`.

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
- `timestamp`: the stored UTC timestamp (naive input is treated as UTC,
  same as the CSV path).

Errors: 422 from FastAPI/Pydantic validation (missing field, wrong type,
negative count, ICU outside 0..100, unparseable timestamp). No other new
error codes.

Backend function (ingestion.py):
`ingest_single_record(record: OperationalRowSchema, db: Session) -> RecordIngestionResponse`.

Simulator (backend/scripts/simulate_live_feed.py):

- CLI: `--api-base` (default `http://localhost:8000`), `--source`
  (default `hospital_operations_synthetic.csv`), `--interval` seconds
  (default 5), `--count` records (default 24).
- Pure function for testing:
  `build_next_record(latest_ts: datetime, source_rows: list[dict]) -> dict`
  returns a JSON-ready dict with the 7 fields.
- Hour-of-week match: `weekday() * 24 + hour` of `latest_ts + 1h`; the
  first source row with that hour-of-week is copied.

Frontend:

- `page.tsx`: `refreshDashboard(showLoading: boolean)`; a `useEffect`
  starts `setInterval(() => refreshDashboard(false), POLL_INTERVAL_MS)` and
  clears it on unmount. Each layer's data and error still update
  independently, as today.
- `POLL_INTERVAL_MS = 10000` constant in page.tsx.
- No new API function is needed for polling. No frontend call to the new
  POST endpoint (the simulator is the only caller).

#### Failure modes

| Input | Behaviour |
| :--- | :--- |
| Bad value (negative, ICU > 100, wrong type, bad timestamp) | 422 with Pydantic detail; nothing written. |
| Missing field | 422; nothing written. |
| Extra unknown field | Ignored (Pydantic default). PROVISIONAL, see NQ-3. |
| Duplicate timestamp | Existing row updated; `action="updated"`; row count unchanged (same as CSV upsert, OPQ-002). |
| Same instant in another offset (e.g. `+05:30`) | Normalised to UTC, so it matches the existing row and updates it. |
| Out-of-order (older than latest) | Stored. Layers keep using the latest row, so current state does not change. Forecast lags are positional (disagreement 3), so an inserted older row in the last 25 hours shifts `rows[1]`/`rows[24]`. Documented, not fixed. |
| Gap (more than 1 hour after latest) | Stored. Same positional-lag caveat. The simulator never creates gaps. |
| Timestamp not on the hour | Accepted, like the CSV path. PROVISIONAL, see NQ-2. |
| Simulator: database empty | `GET /current-state` returns 404; simulator prints "Upload a CSV first" and exits with code 1. No fallback. |
| Simulator: API down | Prints the connection error and exits with code 1. |
| Simulator: POST returns non-200 | Prints status and detail and exits with code 1. |
| Simulator: source CSV missing or has no row for that hour-of-week | Exits with a clear message, code 1. |
| Dashboard: an endpoint fails during a poll | That card shows its error, as today; next poll retries. |
| Dashboard: poll while previous poll in flight | Accepted; each fetch sets its own state. 10 s interval makes overlap unlikely. |

#### Milestones

**M1: Single-record endpoint (REQ-012)**
- Tasks: add `RecordIngestionResponse` to schemas.py; add
  `ingest_single_record` to ingestion.py; add the route in routes.py; add
  backend/tests/test_live_ingest.py.
- Done when: the 5 new tests and all 16 existing tests pass; `/docs` lists
  `POST /api/v1/ingest/record`.

**M2: Simulator (REQ-013)**
- Tasks: add backend/scripts/simulate_live_feed.py; add
  backend/tests/test_simulator.py; add a "Live feed simulator" section to
  README.md with the PowerShell command.
- Done when: the 3 new tests and all previous tests pass; a manual run
  against a local backend with the synthetic CSV loaded posts `--count 3`
  records and `GET /current-state` shows the timestamp advanced by 3 hours.

**M3: Dashboard polling (REQ-014)**
- Tasks: change page.tsx as described above.
- Done when: `npm run lint` and `npm run build` pass, the full backend
  suite passes, and a manual run shows "Latest data" advancing while the
  simulator runs, without loading skeletons flashing.

#### Files

Create:
- backend/tests/test_live_ingest.py
- backend/tests/test_simulator.py
- backend/scripts/simulate_live_feed.py
- docs/loop_log.md (run log)

Change (additions only unless stated):
- backend/app/schemas.py: add `RecordIngestionResponse`.
- backend/app/ingestion.py: add `ingest_single_record`.
- backend/app/routes.py: add one route.
- frontend/src/app/page.tsx: `showLoading` parameter and polling effect.
- README.md: simulator usage section; mention the new endpoint.
- expansion_plan.md: status and "As built".

Must not change:
- plan.md, docs/project_context.md.
- Any existing test file in backend/tests.
- `POST /api/v1/ingest/csv` behaviour and `OperationalRowSchema`.
- The database schema (no new tables or columns), the 4 layers, the model.
- hospital_operations.db, hospital_operations_synthetic.csv.
- requirements.txt and package.json (no new dependencies).

#### Open questions

BLOCKING
- BQ-1: Approve reversing plan.md §2.2 "Conflict 2" (CSV-only ingestion)
  by adding `POST /api/v1/ingest/record`. The roadmap names it, but
  project_context.md requires an approved expansion plan to reverse a
  recorded decision. Approving this plan approves the reversal.

NON-BLOCKING (decided, reversible)
- NQ-1 PROVISIONAL: duplicate timestamp updates the row (upsert) rather
  than returning 409. Why: matches the CSV path and OPQ-002, so both paths
  behave the same.
- NQ-2 PROVISIONAL: timestamps are not forced onto the hour. Why: the CSV
  path does not enforce it either; adding it only here would make the two
  paths disagree.
- NQ-3 PROVISIONAL: unknown extra JSON fields are ignored. Why: Pydantic
  default, no schema change, and `OperationalRowSchema` is shared with the
  CSV path.
- NQ-4 PROVISIONAL: the simulator replays the synthetic CSV row with the
  same hour-of-week instead of random generation. Why: realistic daily and
  weekly pattern, deterministic, and explainable in one sentence.
- NQ-5 PROVISIONAL: poll every 10 s; simulator default interval 5 s. Why:
  short enough to see changes in a demo, light on a local SQLite backend.
- NQ-6 PROVISIONAL: polling instead of WebSockets/SSE. Why: the roadmap
  says "polling", and it needs no new server component.
- NQ-7 PROVISIONAL: no "Live" indicator or toggle in the UI; the existing
  "Latest data" timestamp shows that data is moving. Why: keeps the step
  to the stated scope.
