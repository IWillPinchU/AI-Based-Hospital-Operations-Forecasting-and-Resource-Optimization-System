# Project context for AI assistants

## What this is
College major project, to be demoed and defended in a viva. A hospital
operations decision-support system: current state, ED arrival forecast
(ML), anomaly detection, and resource recommendations, shown on a
dashboard. FastAPI backend, Next.js frontend, SQLite. plan.md describes
the system as built (Milestones 1-5 complete, 16 backend tests passing).

## How we work (rules)
- Plan before building. Build one milestone at a time, then stop and tell
  me how to verify it.
- Do not invent requirements, features, deferred items or future
  enhancements. If something seems missing, ask.
- If plan.md, the code and a suggestion conflict, tell me. Never silently
  change the design or the plan.
- Prefer simple, explainable methods. Test: could the student explain it
  in one or two sentences?
- When told "change only X", change only X and list every change made.
- Never claim something is verified unless it was run or inspected.
- Commands are for Windows PowerShell.

## Decisions already made (do not reintroduce unless an expansion plan says so)
- SQLite via DATABASE_URL, PostgreSQL-compatible code, no Docker. The
  original diagram says PostgreSQL; SQLite is a deliberate v1 choice.
- Tables created with create_all. No Alembic, no snapshot table, no
  orchestrator: each endpoint computes on request.
- No fallback modes: clear HTTP errors instead.
- No prediction intervals and no z-scores. Layer 3 uses deviation % against
  the hour-of-week mean.
- No authentication. Recommendations are advisory only, with a disclaimer.
- Staffing and bed thresholds are PROVISIONAL placeholders in config.py,
  not clinical policy. The data is synthetic (fixed seed).
- The feedback loop is out of scope entirely unless I ask for it.
- No frontend tests. Declined: merging layers into one services.py,
  in-memory SQLite, serving the frontend statically from FastAPI.

## UI design (new UI must match the existing look)
Light theme only. Hospital wayfinding and triage feel. Fonts: Chivo
(headings and numbers, tabular figures) and Atkinson Hyperlegible (body),
self-hosted. Icons: lucide-react, one stroke weight. Severity is always
icon plus text, never color alone. Sentence case, plain words. Avoid:
identical rounded cards with soft shadows, gradients, cream plus orange,
tracked ALL-CAPS labels, numbered markers, "→" on buttons, monospace
labels, fade-in on every section. At most one orchestrated motion.

## Environment
Windows, PowerShell. Python venv at repo root (.\.venv\Scripts\python.exe).
Backend: uvicorn app.main:app --app-dir backend --port 8000.
Frontend: Next.js 16, Tailwind v4, Recharts (cd frontend; npm run dev).
Node v26.13.0, npm 11.20.0.

## Expansion roadmap (one at a time, never build ahead)
1 Live ingestion (single-record POST, simulator, dashboard polling).
2 Decide on multiple departments. 3 History and forecast-vs-actual.
4 Model evaluation against baselines. 5 PostgreSQL and migrations.
6 Real optimizer for Layer 4. 7 Automated retraining. 8 Hardening.
Final vision: real-time data from hospital systems (simulated, since
there is no real hospital feed).

## Known quirks
- A Starlette/httpx deprecation warning in tests is harmless.
- Reverse a decision above only when an approved expansion plan says so.