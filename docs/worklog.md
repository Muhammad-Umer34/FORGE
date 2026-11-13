# FORGE work log

What was done, when and why, newest first. One entry per piece of work. Each entry lists the decisions
it implements (see `decision-log.md`), the commits, how it was checked, and what was left open.
Dates are the commit dates in git.

---

## 2026-11-13 · Evaluation baseline and OpenRouter comparison

**What**
- Langfuse connected (keys in `.env`); every evaluation run is traced with the tags `eval`, the provider, the brief id
  and its group.
- **Bug found by the first baseline run**: 71 of 72 runs failed at once with "GOOGLE_API_KEY is set". The Google SDK
  puts the key in `GOOGLE_API_KEY` for a moment while it builds a Vertex client; with 3 runs in parallel, another
  thread's safety check saw it. Clients are now built one at a time (`gateway._CLIENT_LOCK`); the studio would have hit
  the same failure with two users at once. Test: 40 clients built from 8 threads.
- **OpenRouter in the gateway** → **D-218**: `LLM_PROVIDER=openrouter`, `OPENROUTER_API_KEY`, `langchain-openai==1.7.0`,
  prices of the 5 allowed models (from openrouter.ai, 2026-11-13). All 4 tried models return valid structured output.
- **Baseline and comparison**, 24 briefs x 3 runs per provider:

| 72 runs each (24 briefs x 3) | Gemini: 2.5 Pro (planning) + 3.8 Flash (clarification) | OpenRouter: MiMo v2.6 Pro (planning) + GPT-6 Luna (clarification) |
|---|---|---|
| Correct outcome | 93.1% | 93.1% |
| Valid plans (briefs that should plan) | 92.4% | 92.4% |
| Must-feature coverage | 92.0% | 89.9% |
| Fix rounds per run | 0 | 0.28 |
| Model calls per run | 7.8 | 5.1 |
| Cost per run (total) | $0.027 ($1.97) | $0.009 ($0.68) |
| Time per run | 47 s | 134 s (booking briefs 420 s) |
| Failures | 5, all the hero relevance rule (check 7) | dropped must sections (check 3), data links written as `x_id -> table` (check 9), a button rule misfire, one reply cut at 131k tokens |

**Why** Phase 1 asked for baseline numbers; the OpenRouter key offered cheaper models, so both were measured on the
same set before choosing.

**Decision** Gemini stays the default (D-218); OpenRouter is one `.env` change away.

**Checked** 2 new gateway tests (OpenRouter client; parallel Vertex clients); full suite passes except the 61
database tests (test database down). Results: `scripts/runs/eval_20261113_130210.json` (Gemini) and
`scripts/runs/eval_openrouter_20261113_133943.json` (gitignored).

**Open**
- New issues from the runs: KI-20 (hero relevance rule, every Gemini failure), KI-21 (`cta_body` read as a button),
  KI-22 (link format), KI-23 (no output-token limit).
- The OpenRouter key expires on 2026-12-05.

---

## 2026-11-13 · Phase 1: make runs visible and measurable

**What** Phase 1 of the roadmap in `D:/FYP/reports/FORGE architecture lessons from peers.md`.
- **Tracing** → **D-215**: `agents/tracing.py` builds each run's config with a Langfuse callback handler when the
  `LANGFUSE_*` keys are set; used by the studio API (`backend/routes/requests.py`), `run_forge_once.py` and the
  evaluation runner. `langfuse==5.1.0` added to `requirements.txt`.
- **Cost and spending cap** → **D-216**: price table and cost per call in `gateway.py`; `max_run_cost_usd` ($1.00)
  checked before every call; a spent budget ends the run as failed with its own message. Found while testing: the
  planning subgraph never sees the run total (its input leaves out `usage`, FX-01), so the retrieval step now hands
  Planning what was already spent (`PlanningState.spent_before_usd`).
- **Evaluation set** → **D-217**: `scripts/eval_briefs.json` (24 briefs) and `scripts/run_eval.py`.

**Why** Without traces a failed run had to be read out of checkpoints by hand; without a cost cap a builder loop
could spend the credits; without fixed briefs and numbers no change can be shown to be an improvement, and the
thesis needs measured results.

**Checked** 33 new tests (cost, budget refusal, budget hand-over to Planning, tracing on and off, every brief uses
real catalogue ids): 385 pass; the 61 database tests were not run (test database down). One live evaluation run
(booking-01): planned correctly, 0 questions, 8 model calls, $0.030, 42 s.

**Open**
- Create the Langfuse project and put its keys in `.env` (tracing is off until then).
- Run the full baseline (24 briefs × 3, about $2–4) and record the numbers here.
- Prices of `gemini-3.1-flash-lite` not published; priced as Flash for now.

---

## 2026-11-13 · Phase 0: stop losing valid runs

**What** Phase 0 of the roadmap in `D:/FYP/reports/FORGE architecture lessons from peers.md`: the bugs that end
good runs or quietly spoil plans, plus two scope changes the team made while approving it.
- **No page limit, no test cap** → **D-212**. Removed `max_pages` and `max_test_cases` with every use (page-limit
  question and answer, brief check, planning check 1, prompts, test trimming). Fixes KI-04 and KI-05.
- **Precise capability matching** (KI-01): the safety net matches whole words, and short all-caps names (POS, UPS,
  TCS) only in capitals. "Open job positions", "Daily soups special" and "Striped kurta range" stay custom features.
- **Custom feature ids** (KI-06): from the name when it gives one, otherwise from the item id; a repeat gets the
  item id added. Urdu and emoji names no longer collide on `custom-item`.
- **Button verbs** (KI-16): "Let's talk" reads as *let*; accept, decline, donate, enroll, register and a few more
  are allowed.
- **Owner lists per component** (KI-02) → **D-213**.
- **Plan code fixes** (KI-03, KI-11, KI-14): `tidy` lower-cases every page reference; `complete_data` keeps linked
  stored types all the way down; required texts the model leaves empty go to the rewrite round; the data prompt
  asks for `feature_ids`. Done inside the existing `tidy`, `complete_data` and `texts` instead of a new
  `normalise_plan` node, which is less code for the same effect.
- **Strict fix guard** (KI-19) → **D-214**.

**Why** Each item ended a run the user had already invested in, or gave builders a wrong plan. The research found
that deterministic gates must be precise, because a wrong rule fires the same way every time and no retry saves it.

**Checked** 17 new tests (one or more per item): 352 pass; the 61 database tests were not run (test database down).

**Open**
- Re-run the bakery and salon requests live.
- Not changed: custom-feature limit (5), API routes (10), stored types (6), one plan change.
- Next: Phase 1 (tracing, cost per run, evaluation set).

---

## 2026-11-08 · Live planning tests, data-contract fixes, project audit, this documentation

**What**
- First live runs of the Planning Agent through the studio (hair salon, bakery). Three runs failed with
  "We could not finish planning your site"; each was traced from its saved checkpoint:
  - req_ec94cad5cb4e: the model gave Home the route `/home`; two fix rounds kept it → **D-210**.
  - req_c89c88eead73 and req_ec38c1bbb3d4: good first designs failed check 8 (POST routes with empty
    `used_by`, feature ids in `used_by`, no form rules); Flash fix rounds then rewrote the plans badly
    (one hero section; no sections at all) → **D-209, D-211**.
- Fixes: code forces Home to `/` and numbers the menu; `complete_data` finishes the data contract; a fix
  round that adds problems is thrown away; fix rounds use `gemini-2.5-pro`; clearer data prompt.
- Full audit of the Clarification Agent, Planning Agent, catalogue scope and comparable AI builders:
  report `D:/FYP/reports/FORGE agent scope review.md` (notes in `D:/FYP/research_notes/FORGE agent scope review/`).
  Its open bugs and limits are tracked in `known-issues.md`.
- Documentation system set up (`docs/`): the decision log moved here from the v6 plan, this work log,
  known issues, and the logging rules in `README.md`.

**Why** Live runs showed the model's designs were good but small rule gaps ended planning; code can
apply fixed rules exactly, while model fix rounds were unreliable (also found in research: self-repair
without outside feedback often makes output worse).

**Checked** Both failed live designs reproduced as tests now pass every check with no fix round;
a test proves a worse fix is discarded; 335 tests pass (61 database tests not run: test database down).

**Open**
- Re-run the bakery and salon requests live to confirm 3 model calls and a plan screen.
- Work through `known-issues.md` (quick fixes first).
- Commits: f06eda9 (planning fixes, D-209 – D-211) and the docs commit that added this folder.

---

## 2026-11-04 · Planning Agent built and wired into the run (Phases 4–6), first live testing

**What**
- Phase 4 (8ac55c2): planning subgraph in `agents/planning/`: input check and fixed parts in code,
  3 model calls (site design, data and API, text), 16 code checks, up to 2 fix rounds, one text rewrite,
  plan-approval pause with one change, freeze → **D-204**. Website text pitch rules: hero tied to the
  business, no generic phrases, no invented facts, button verbs, no repeated titles → **D-205**.
- Phase 5 (b04c43b): the run continues after the brief: retrieval → planning → stops at GENERATING.
  New statuses `awaiting_plan_approval` and `planned` (migration 0007), `POST .../plan`, plan screen
  `PlanReview.tsx`, steps Describe · Answer · Confirm · Plan · Build → **D-206**. A bug found while
  testing: the planning subgraph sent the run's whole usage total back, counting calls twice; fixed with
  an input schema without `usage`.
- Phase 6 (55acfcc): backend and agents READMEs, project status, benchmark wording ("comparing
  candidate LLMs", not a single-agent baseline).
- Studio fixes (d782331): reload the real state after a 409 → **D-207**; extension attributes on
  `<body>` → **D-208**.
- Migration 0007 applied to the app database (after Supabase un-paused it).
- Model probe on Vertex AI: only `gemini-2.5-pro` and `gemini-3.1-pro-preview` answer among Pro models;
  `PLANNING_MODEL=gemini-2.5-pro` set in `.env`.
- Local run setup: `D:/FYP/.claude/launch.json` starts the backend (`python -m backend.main`) and the
  frontend (`npm run dev`); outside the repo.

**Why** Plan v2 (`D:/FYP/reports/Planning Agent plan v2.pdf`): a strong model designs, code places fixed
parts and checks everything, the user approves before building. One run per request keeps pauses,
resume and Start over working for every step.

**Checked** 331 tests pass; full-graph test goes confirm → plan → approve → GENERATING. Database route
tests written but not run (test database paused).

**Open** Builder agents (frontend, backend, database) are stubs; business details form not built.

---

## 2026-11-03 · Context Retrieval (Phase 3)

**What** (c53acd4) Code-only retrieval in `agents/retrieval/ranker.py`: a catalogued feature gets every
component of its feature; a custom feature gets up to 3 close keyword matches or none. `Catalogue` now
carries each component's details → **D-203**.

**Why** With 46 components the catalogue already knows the answer; embeddings would add a dependency
and a model call for little gain.

**Checked** 5 retrieval tests.

---

## 2026-11-02 · Component Needs List and typed Build Plan (Phases 1–2)

**What**
- Phase 1 (e62303c): `components/component_needs.json`, generated from the components' TypeScript props
  by `build_component_needs.py`: every input's kind (copy, fact, list, image, setting, live, code),
  type, required flag, length limit and content key; 49 components, 372 inputs → **D-201**.
- Phase 2 (778bedb): typed `BuildPlan` in `agents/state.py` (pages, sections, custom specs with their own
  needs, form fields, text slots, data entities, API routes, form rules, dashboard views, work plan, test
  map), the `planning` working slice, plan views per generator, new limits, `STATE_VERSION` 2 → **D-202**.
- Planning requirements added by the team: custom components get needs of the same kinds as catalogue
  ones; website text, especially the hero headline, must be a strong pitch for the exact business type.

**Why** The planner must know what every part needs to render fully (business details form, text,
no-empty-component check); typed models let code check every plan.

**Checked** 98 needs tests (file always matches the components' code), 7 plan-model tests.

---

## 2026-10-23 · Persistence, resume and one website per project

**What** (a0b55a6) Runs saved in PostgreSQL every step (LangGraph `AsyncPostgresSaver`); a run cut off
by a crash or outage is "paused" and continues from its last step (`POST .../resume`); cancel; start-up
repair of stuck requests; one project = one website (409 `website_in_progress`, Start-over dialog);
migration 0006 → **D-197 – D-200**. Supabase session pooler with a reset password; psycopg needs a
SelectorEventLoop on Windows.

**Why** A crash test lost a run and let a second browser start a competing website in the same project.

**Report** `D:/FYP/reports/FORGE persistence plan.pdf`.

---

## 2026-10-21 · Code audit fixes

**What** (11f0d19) The visitor's real address reaches the backend; a failed new request is saved as
failed and not counted against limits; input fixes → **D-195, D-196**.

---

## 2026-10-20 · Cost and abuse limits

**What** (7b00488) Rate limits as PostgreSQL counters: model-spending limits per user and per app,
sign-up and forgot-password limits, lockout per address, size limits, daily email cap → **D-189 – D-194**.

---

## 2026-10-19 · Email verification and password reset

**What** (8c8b653) Verification and reset links by email over SMTP; unverified users can sign in but
not create projects or run requests → **D-185 – D-188**.

---

## 2026-10-17 · Clarification Agent, theming, accounts and projects

**What**
- FORGE-1 codebase with the Clarification Agent (design v6): detector-first slots, questions, brief,
  code checks, confirmation screen, acceptance tests (e06c38d) → **D-101 – D-146**.
- Clarification screen as the frontend's main page (50d2c52) → **D-147**; review-note fixes (1623a2a)
  → **D-148, D-149**; greetings and off-topic messages handled before clarification (9c998ad) →
  **D-150 – D-154**.
- Themes from parameters with guaranteed WCAG contrast (02b6fff) → **D-155 – D-162**; colours from a
  logo, screenshot or a website the user likes (123d58f) → **D-163 – D-171**.
- Users and projects with a 3-project limit on Supabase (0e4faa6) → **D-172 – D-175**; JWT sign-in with
  refresh rotation (ca0b25e) → **D-176 – D-178**; requests belong to projects (0698e08) → **D-179, D-180**;
  sign-in, register and project screens (f2edf45) → **D-181 – D-183**; model calls on Vertex AI credits
  (7fb6569) → **D-184**.

**Design** `D:/FYP/FORGE-DOCUMENTS/FORGE_Clarification_Agent_Plan_v6.md` (+ PDF); implementation
notes in `FORGE-DOCUMENTS/Implementation details - 01/02`.

---

## 2026-10-16 · Foundations and the v6 design

**What** One `.env`, package imports, own venv with pinned requirements, CORS from settings, no human
escalation, research kept outside the codebase → **D-001 – D-008**. Clarification Agent v6 designed
(16 flaws of v5 fixed).
