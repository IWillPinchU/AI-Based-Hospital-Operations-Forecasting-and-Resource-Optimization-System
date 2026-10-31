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
  Check with git diff and searches, not from memory.
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

## Git workflow

### Branches
- main: never touched by the AI. Only the student merges into it.
- expansion: integration branch. The AI may merge a finished exp/ branch
  into it, but only through the merge gate below. No direct commits on it.
- exp/NN-name (for example exp/01-live-ingestion): the AI's working
  branch. All AI commits go here.
- Hooks block commits and merges on main and master. Never bypass them.
- Checkpoints are commits on the working branch. Each finished milestone
  gets a tag: cp-NN-mM (for example cp-01-m1).
- v1-demo is the tag of the viva-ready version. Never move or delete it.

### Forbidden git actions
Never use: --no-verify, force-push, git reset --hard, git branch -D,
git rebase on shared branches, deletion of any tag, git checkout main,
or any commit made directly on expansion. Checking out expansion is
allowed only to perform a gated merge.
Before every commit, verify the current branch is an exp/ branch.

## Rules for autonomous runs
- One expansion step per run. First assess the repository and write that
  step's plan in expansion_plan.md. Then build its milestones in order:
  implement the next task, run the full test suite, commit a checkpoint
  when it passes. After each milestone, run the Merge gate and merge into
  expansion, then continue with the next milestone of the SAME step.
  Never start the next step.
- If tests fail, fix the code, never the tests. Do not edit, weaken,
  skip or delete existing tests. New tests may be added.
- Never touch hospital_operations.db or any real data file. Tests use
  in-memory databases only.
- Do not edit plan.md or this file. Only update expansion_plan.md status
  if the run is told to.
- No new dependencies without logging the package and the reason.
- Keep docs/loop_log.md: tasks done, commands run, test results, every
  file changed, dependencies added, and a plain two-sentence explanation
  of each new component.
- Stop immediately and write docs/BLOCKED.md if: the same problem fails
  3 times, a decision is needed that is not in expansion_plan.md, plan.md
  and the code disagree, or a decision recorded in this file would have to
  change.
- State exact commands and results. Do not claim anything is verified
  unless it was actually run.
- After finishing, give a summary and how to verify.

## Merge gate (the AI merges into expansion only, never into main)
Merge the finished exp/ branch into expansion only when ALL of these are
true, checked by running the commands now (not from memory):
1. docs/BLOCKED.md does not exist and the milestone's "Done when" is met.
2. The full test suite passes, run fresh on the branch.
3. git diff expansion --name-status -- backend/tests shows only A (added)
   files: no D and no M. If an existing test genuinely needs to change,
   write docs/BLOCKED.md instead of merging.
4. git diff expansion --stat shows no change to plan.md or
   docs/project_context.md.
5. git ls-files shows no .db, .env.local, node_modules, .next or .joblib
   files tracked.
6. docs/loop_log.md was updated this run and includes a plain
   two-sentence explanation of each new component.
7. The working tree is clean.

Merge procedure: tag expansion as pre-merge-NN-mM, git checkout expansion,
git merge --no-ff <exp branch>, run the full test suite again on expansion,
then tag merged-NN-mM. If the merge conflicts, run git merge --abort and
write docs/BLOCKED.md. If the tests fail after the merge, run
git revert -m 1 HEAD (never git reset --hard), then write docs/BLOCKED.md.
Never delete the exp branch or any tag. Never merge into main.

## Student's gate
Before merging expansion into main, the student reviews
git log --oneline main..expansion, the loop_log.md entries and the
two-sentence explanations, and runs the app. Merging into main is always
the student's own action. If the student asks for an explanation of any
component, give a plain two-sentence description and offer a simpler
implementation if it is hard to explain.