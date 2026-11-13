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

Every model call goes through `gateway.py`; agents never write to the database (D-133).

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
| `assemble.py` | Tidies the model's design and builds the `BuildPlan`: sections in order, text slots, consent on forms with personal data, work plan, test map, not-built list |
| `content_schema.py` | The business details form, derived from the Component Needs List (`components/component_needs.json`, D-201) and the needs of each custom part |
| `checks.py` | The 16 plan checks; each problem is one plain sentence for the fix round and the error log |
| `texts.py` | The pitch rules for website text (D-205) and the choice of the hero headline |
| `nodes.py`, `graph.py` | The subgraph: 3 model calls (site, data and API, text), at most 2 fix rounds and 1 text rewrite, the plan-approval pause (one change allowed), and freeze |

The plan's types live in `state.py` (`BuildPlan`, `PlanningState`, D-202). Tests: `tests/test_planning.py` (fake model),
`tests/test_clarification_flow.py` (the whole run through plan approval).
