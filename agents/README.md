# Agents
Multi-Agent intelligence modules: Clarification, Planning, Generation, Verification.

## The run so far

One website request is one LangGraph run (`orchestrator/graph.py`), saved step by step in PostgreSQL:

1. **Clarification** (`clarification/`): asks at most a few questions, shows the confirmation screen and freezes the
   brief with its acceptance tests.
2. **Context Retrieval** (`retrieval/ranker.py`, D-203): code only. A catalogued feature gets every component of that
   feature; a custom feature gets up to 3 close keyword matches, or none.
3. **Planning** (`planning/`, D-204): designs the whole site on paper and pauses for the user's approval.
4. The run stops at `GENERATING` until the builder agents exist.

Every model call goes through `gateway.py`; agents never write to the database (D-133). `LLM_PROVIDER` picks
Vertex AI (default), AI Studio or OpenRouter (D-218); the models per task are set in `.env`.

## Building sites (Phase 3, in progress)

- **Site template** (`site_template/`, D-235): the Next.js project every generated site starts from; the catalogue
  components are copied in at build time. Install its packages once: `npm install` in `site_template/`.
- **Build worker** (`build_worker.py`, D-231): builds a site in its own folder under `builds/`, type check then
  `next build`, and returns file, line and message for every error.
- **File store** (`file_store.py`, D-234, D-236): builder steps keep files here, never in the state; the API sets the
  PostgreSQL store, tests use the memory store.
- **Build step** (`orchestrator/graph.py: build_site`, D-233): runs after the plan is approved, in the background,
  with progress events; until the builders exist it saves the approved plan as `forge/plan.json`.
- **Code from the model** (`gateway.call_files`, `call_files_parallel`, D-228): whole files as `<file path>` blocks,
  at most 3 calls at once within the run's budget.

## Watching and measuring runs (Phase 1)

- **Tracing** (`tracing.py`, D-215): when `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set in `.env`
  (`LANGFUSE_BASE_URL` picks Langfuse Cloud or a self-hosted server), every step and model call of a run is sent to
  Langfuse, grouped by request id (one session per request). Without the keys nothing changes.
- **Cost and budget** (`gateway.py`, D-216): each call's cost comes from the price table `PRICES` (USD per 1M tokens,
  checked 2026-11-13); the run total is `usage.estimated_cost_usd`. Before every call the gateway refuses once the run
  has spent `Limits.max_run_cost_usd` ($1.00, placeholder), and the run ends as failed with a plain message.
- **Evaluation set** (`scripts/eval_briefs.json`, `scripts/run_eval.py`, D-217): 24 fixed briefs in 8 groups, each
  with the expected outcome, the features the plan must and must not contain, and the answer key of a strict
  simulated owner. `run_eval.py` runs them (3 times each by default) and reports correct outcomes, valid plans,
  feature coverage, questions, calls, fix rounds, failed checks, cost and time.

## Planning Agent (`planning/`)

| Module | What it does |
|---|---|
| `fixed.py` | Checks the input; places the parts every site has (header, footer, site-wide parts, hero first on Home, a page header on inner pages) and lists the components the model may choose from |
| `schemas.py` | The formats the model must answer in: site design, data and API design, plan fix, website text, plan decision |
| `prompts.py` | The prompts and the standard starting designs for known forms (booking, contact, order, newsletter, blog, events) |
| `assemble.py` | Tidies the model's design and builds the `BuildPlan`: sections in order, a search head on every page and a 404 page (D-221), text slots, consent on forms with personal data, accessibility rules, work plan, test map, not-built list, assumptions |
| `content_schema.py` | The business details form, derived from the Component Needs List (`components/component_needs.json`, D-201) and the needs of each custom part |
| `checks.py` | The 18 plan checks (17: a search title and description on every page, 18: one H1 per page, D-221); each problem is one plain sentence for the fix round and the error log |
| `texts.py` | The pitch rules for website text (D-205) and the choice of the hero headline |
| `nodes.py`, `graph.py` | The subgraph: 3 model calls (site, data and API, text), at most 2 fix rounds and 1 text rewrite, the plan-approval pause (one change allowed), and freeze. Fix rounds and the user's change return a patch of only what changes (`schemas.PlanPatch`, merged by `assemble.apply_patch`, D-220); after a change only the changed sections get new text, and a change that breaks the plan or its text is undone |

The plan's types live in `state.py` (`BuildPlan`, `PlanningState`, D-202). Tests: `tests/test_planning.py` (fake model),
`tests/test_clarification_flow.py` (the whole run through plan approval).
