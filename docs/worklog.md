# FORGE work log

What was done, when and why, newest first. One entry per piece of work. Each entry lists the decisions
it implements (see `decision-log.md`), the commits, how it was checked, and what was left open.
Dates are the commit dates in git.

---

## 2026-11-25 · Backend Agent, day 6: the evaluation's backend stage (D2)

**What**
- `scripts/run_data_eval.py` backend stage: real site-data calls per planned site (saved, wrong key, rule broken).
- Fixes found by it: long rule and trigger names (refused, and trigger order broken); GET routes on recipe tables
  take no visitor fields.

**Checked** D2: 7 of 12 planned, 36/36 rule tests, 8/8 owner answers, backend 23/24 (the groomer, fixed after,
3/3 offline). Full suite 697 passed before the fixes; compile, planning, backend and data-check tests 129 passed
after.

Then D-251: code adds a field for a visitor detail no field holds. **D3: 12 of 12 planned, backend 42/42.**

**Open** Commit; the Integration Agent plan.

---

## 2026-11-25 · Backend Agent, day 5: the owner's dashboard (D-250)

**What**
- Owner-only routes `/api/projects/{id}/data` (lists, rows, status moves, add, edit, remove, clear samples) in
  `backend/routes/owner_data.py`, with the service functions in `backend/services/site_data.py`.
- Studio page `/projects/{id}/data` (`SiteData.tsx`), reached from the header's "Site data" link.
- Sample clearing keeps only the sample rows real rows still use, and says how many.

**Checked** Live on Glow Salon: the real booking shown, New → Confirmed (only allowed moves offered), a stylist
added, 14 sample rows removed and 2 kept, the public stylist list updated. Owner tests 6, studio type check and
lint clean.

**Open** Day 6: the evaluation's backend stage (D2), full suite.

---

## 2026-11-24 · Backend Agent, day 4: a live booking (D-247 - D-249)

**What**
- Migration 0009 on Supabase (with Umar's OK); local `forge_sites` for site storage; `.env` switches.
- A fresh preview key when a project is reopened.
- `DataForm` for any section a recipe POST route serves.
- Keys cached and rate limits counted in memory (Supabase connections took about 7 s).
- The site waits 20 s; missing fields get the owner's wording.

**Checked** Live in the studio and the Glow Salon preview:
- free times shown, a booking saved as New with its end time;
- a double booking and a Sunday booking refused in plain words.

Tests: backend agent 10, site data 16.

**Open** KI-40 - KI-42; days 5-6.

---

## 2026-11-24 · Backend Agent, day 3: DataForm (D-249)

**What** `site_template/components/DataForm.tsx`; the compiler renders it for recipe form sections and writes
`lib/schemas.ts`.

**Checked** A full salon site with `DataForm` type-checks and builds for production; full suite 688 passed; studio
type check clean.

**Open** Day 4 needs migration 0009 on FORGE's database and the `.env` switches.

---

## 2026-11-24 · Backend Agent, day 2: availability, the Backend Agent's files, the backend gate (D-247, D-248)

**What**
- `site_data.availability` and its route.
- `agents/backend_generator/agent.py` and `gate.py`; the old stubs removed.
- Site template: `lib/forge.ts`, `lib/schemas.ts`, `app/api/data/[table]/route.ts`, `.../availability/route.ts`;
  `lib/store.ts` removed.
- Planning: real route paths, missing recipe POST routes made by code.
- `build_site` runs the Database, Backend and Frontend agents in turn.

**Checked** `tests/test_backend_agent.py` (7, incl. a real type-check and the gate on local PostgreSQL); full suite
687 passed.

**Open** Days 3-6 (journal #34).

---

## 2026-11-24 · Backend Agent, day 1: storage registry and the site data API (D-247)

**What**
- Migration 0009 `site_storage`; `SiteStorage` table.
- `provision.register` / `new_preview_key`; owners may delete rows of their own lists (grant).
- `backend/services/site_data.py` and `backend/routes/site_data.py`.
- The contract marks visitor fields.
- Settings `SITE_DB_URL`, `FORGE_API_URL` and the site rate limits.
- The preview gets `FORGE_SITE_KEY` from memory.

**Why** The plan approved on 2026-11-24 (`D:\FYP\reports\FORGE Backend Agent plan.md`).

**Checked** `tests/test_site_data.py` (14, local PostgreSQL); full suite 679 passed.

**Open** Days 2-6 (journal #34).

---

## 2026-11-23 · Details visitors give are kept (D-246)

**What**
- `IntakeOutput.visitor_details`, stored on the clarification state and the brief, with a summary line.
- A planner rule; plan check 30 with `data_patterns.detail_covered`.

**Why** The pet groomer's request named the pet's name, breed and age, and the plan had none of them: they were
lost in clarification.

**Checked** New tests for check 30, the matching and the summary line; 583 tests without the database pass. Live:
the plan added `pet_name`, `breed` and `age`. The full data set is being rerun.

---

## 2026-11-23 · Database Agent, day 7: data evaluation (D-242 - D-245)

**What**
- `scripts/data_briefs.json` (12 requests, six families) and `scripts/run_data_eval.py`, which plans each one,
  stops at the plan screen and proves its data with the database gate.
- Evaluations no longer start previews or builds (`run_eval.py`); the simulated owner answers data questions.
- A catalogue list that clashes with another recipe's own list gives way (`data_patterns.expand`).

**Why** The report needs evidence that owners get the data they need, with every rule enforced.

**Checked** D1: 11 of 12 planned, 50 of 50 rule tests, 17 of 17 owner answers kept, 100% coverage
(`docs/eval-runs/data01_first_baseline.json`). Full suite green.

**Open** Pet groomer rerun after the rate limit; KI-35, KI-38, KI-39.

---

## 2026-11-22 · Database Agent, day 6: "What your site will keep" (D-244)

**What**
- `agents/planning/data_edits.py`: add or remove fields, required or optional, rules on or off, rule numbers, undo
  (replayed edits), and the screen view.
- `data_edit` decision on `POST /plan`; `assemble.route_fields` keeps routes and form rules in step with the edits.
- `DataKeep.tsx` panel on the plan screen.
- Locking only when every answer behind it is the owner's; settings lists not edited.

**Checked** 21 tests; studio type check and lint; live Glow Salon run (questions, panel, add, number, undo, build
with database files).

**Open** KI-39 (edits about 10 s); day 7: data evaluation.

---

## 2026-11-22 · Database Agent, days 4-5: SQL compiler, gate, own schema per site (D-243, D-245)

**What**
- `agents/database_generator/`:
  - `compile.py`: `schema.sql`, `schema.json` and a Mermaid ER diagram, by code only;
  - `seed.py`: sample rows that pass every rule;
  - `gate.py`: a scratch schema, one breaking attempt per rule, rolled back;
  - `provision.py`: `site_<project>` and its role; a rebuild keeps real data; `drop`;
  - `agent.py`: the build step.
- `build_site` runs the Database Agent before the Frontend Agent.
- `FORGE_DATABASE` / `RunConfig.database`; deleting a project drops its storage.
- Planner: worked-out fields (`end_at`, `status`) are not asked of visitors.
- Test database: local `forge_test` created; the dead `TEST_DATABASE_URL` line commented out; the old database
  tests repaired (streaming fakes, background session).

**Why** The Database Agent must turn the owner's data choices into real, safe storage, with proof.

**Checked** 29 compiler, 17 gate (every recipe × every switch value on PostgreSQL), 7 provisioning and agent tests;
full suite incl. database tests: 639 passed.

**Open** KI-35 - KI-38. Day 6: review panel (journal #33).

---

## 2026-11-22 · Database Agent, days 2-3: data checks, data questions, planning call 2 (D-242, D-244)

**What**
- Plan checks 24-29 (`checks._data_model`); `BuildPlan.data_recipes` and `data_problems`.
- Kind-F data questions (`slots.data_gap`), `data_choices`, and one summary line per answer.
- Planning call 2 returns recipes, switches, renames, extra fields and custom record types (`planning/schemas.py`);
  `data_patterns.build` and `prompt_view`; prompt rewritten; `DATA_STARTERS` removed.
- Code sets the route fields of recipe record types, and a recipe's record types stay together.

**Why** Owners shape the data; the model only picks from menus.

**Checked** New tests for checks 24-29, data questions, a salon planned from the recipe, and check 29; the full
fast suite passes (523). Live: 6 requests gave 5 of 6 planned; after the route-field fix, 3 of 3 planned with
100% coverage (scripts/runs/eval_vertex_20261122_193714.json). Those runs were slow because evaluations
also built the site after approval (fixed on day 7, journal #33 step 14).

**Open** Day 4: SQL compiler (journal #33).

---

## 2026-11-22 · Database Agent, day 1: data model v2 and recipes (D-242)

**What**
- `agents/state.py`:
  - data model v2: field options, links, on-delete, unique, default, min/max, locked;
  - `DataRule` with 11 rule kinds; record type role, label and recipe;
  - limits raised; `ClarifiedBrief.data_choices`; question kind F.
- `components/data_patterns.json`: 14 recipes in 6 families, with switches and questions.
- `agents/planning/data_patterns.py`: expansion, rule sentences, compile-safety checks (20-23, 26).

**Why** Owners must shape complex data, and code must be able to enforce every rule. Plan:
`D:\FYP\reports\FORGE Database Agent plan.md`.

**Checked** `tests/test_data_patterns.py` (29 tests: every recipe with every combination of switch values);
the full fast suite passes (513).

**Open** Day 2: planner checks 24-28. Days 3-7: planning call 2, data questions, SQL compiler, gate, review
panel, evaluation (journal #33).

---

## 2026-11-20 · Frontend Agent: custom parts written by the model (D-228 - D-230, D-241)

**What** The rest of the Frontend Agent (Phase 3 items 3.4 - 3.6, 3.8):
- `custom_writer.py`: one model call per custom part or showcase section, at most 3 at once, prompt rendered from
  the plan; props interface written by code from the part's needs; replies accepted only inside the part's folder
  with the right export.
- `postprocess.py`: imports, icons (checked against the installed list), colours, paths, packages, and a keyboard
  check for clickable divs.
- `gate.py`: a code-checks layer (at most 2 rounds), then type check and production build with "Did you mean" fixed
  by code, up to 4 model fix rounds per part (a worse fix discarded), and a fallback section for a part that still
  fails.
- `compiler.py` imports written parts; `agent.py` writes, cleans and gates them and returns their cost to the run;
  gateway tasks `frontend_custom` / `frontend_fix`.
- `scripts/run_builder_eval.py` + `scripts/builder_briefs.json` (9 requests) and the model-written parts saved under
  `scripts/runs/builder_parts/`.
- Preview: a fresh folder per start; sample prices and names made useful for interactive parts.

**Why** Custom parts are the only model-written code; they must be built and checked like the rest, and the report
needs real builder numbers (Chapters 7 and 9).

**Checked** New tests: writer contract 4, post-processors 5, gate 7; all fast tests pass; all 49 library parts still
type-check. Builder evaluation B1: 9 of 9 sites built first time, 3 of 3 custom parts in site, 97% of files by code.
Looked at the parts in the browser (calculator totals correctly, keyboard-reachable after the fix).

**Open** KI-34 (fix rounds and fallbacks not yet exercised live); journal #32.

---

## 2026-11-15 · Reopening a built site; database connection limits

**What** Reopening a built project showed no site (reported by Umar). Fixed the studio's reopen (it checked status
`complete`; a built request is `planned`) so it always asks the backend for a live preview, which restarts it from the
saved files. While testing, found Supabase's session pooler limit (15 clients, `EMAXCONNSESSION`): FORGE's three
pools could open 23, and restarts and network drops left stuck sessions. Capped the pools (app engine 6,
checkpointer 4, file store 2), made the checkpointer and file store test pooled connections before use, and the
preview route answers 503 instead of crashing when the database is unreachable. Ended the 15 stuck sessions (with
Umar's OK).

**Checked** Reopened the built law-firm project: the live site came back in the studio. Affected tests pass.

**Open** None from this; journal issue 31, steps 17–24.

---

## 2026-11-15 · The frontend agent, with a live preview (D-240)

**What** Phase 3 Group 3, item 3.1 plus a live preview, for the supervisor demo. Backend and database agents wait.
- `agents/frontend_generator/compiler.py`: an approved plan in, the site's files out, no model call (globals.css from
  the theme, layout with the direction and site-wide parts, one page per route with props as JSON literals,
  not-found, sitemap, robots, content/site.json). Props from the plan's texts, sample content shaped to each input's
  type, settings shaped to their type, links and menu from the pages, breadcrumbs, readable placeholder samples.
  Custom parts show a call-to-action fallback until the custom-part writer exists. Old stubs deleted.
- `agents/frontend_generator/photos.py`: photo dealer (stock photos once a key exists; theme-tinted placeholders now).
- `agents/frontend_generator/agent.py`: the run: input summary event, compile, file store, live preview, gate.
- `agents/preview.py`: `next dev --webpack` in a worker folder; pages written one by one update the open page.
- `build_site` calls the agent; `RunConfig.preview/build_gate` from `FORGE_PREVIEW`/`FORGE_BUILD_GATE` (off by
  default, so tests never start servers). Backend reload watches only code; previews stopped on shutdown;
  `POST .../preview` restarts a preview from the saved files.
- Studio: `BuildPanel` (progress, "what the frontend agent received", live preview frame), replay on reopen.
- `scripts/frontend_demo.py`: the same run outside the studio, the demo backup.

**Why** The demo needs one live run from request to running site; every file made by code can be type-checked.

**Checked** 11 frontend tests (9 compiler unit tests; all 49 components type-check with compiler-made props, settings
fed as strings like the planner); all non-database tests pass. Real salon plan: type check and production build pass.
Full run in the studio (Italian restaurant): questions, brief, plan, approval, 11 files, live preview, type check 4 s,
production build 20 s.

**Open** KI-30 (forms store nothing), KI-31 (photos need an Unsplash key), KI-32 (preview restart not checked end to
end), KI-33 (home page with only a hero). Journal: issue 31.

---

## 2026-11-15 · Design variety: code deals the direction (D-239)

**What** Fixed KI-29. Research first (`D:/FYP/reports/Reducing sameness in AI site designs.md`, four subagents):
a tuned model asked once returns its favourite look, so the random draws move into code.
- `components/design_presets.json`: 8 business families plus general, 4 curated presets each (4–5 fixed choices),
  presets of a family share at most 3 fixed choices.
- `agents/planning/direction.py`: family from the business type, a seeded preset pick that favours the least-used
  preset among recent sites of that family, open choices drawn in the family's range, `settle` for the model's at
  most 2 reasoned changes (in range, not on a locked choice) and the footer from page count.
- The planner deals the start once per site and passes it to the site-design call; `build_plan` settles the
  model's direction against it. A reference site's measured choices (corners, image corners, bands, headline size)
  override and lock; `reference_style.py` gained those three new measurements.
- `run_eval.py`: variety metrics (same- vs cross-family match over the 8 varied choices, most-common option per
  choice, model change rate), and it now writes the rows before the summary so a summary bug cannot lose a run.

**Why** Left free, the model gave every site nearly the same look (83% → 70–74%); prompts did not move it (D-239).

**Checked** 96 direction/planning tests and all 451 non-database tests pass. Evaluation run 9: direction sameness
**44%** (near the ~40% random floor), was ~70%; hero split 26% (was 74%); 30 of 36 presets used; real correctness
98.1% (3 of 4 wrong were Gemini rate-limit outages, 1 real SEO-length failure). References: 2 of 3 applied and
locked their measured choices.

**Open**
- Images still 74% rounded; the model spends its edits on corners (35%) and images (33%), pulling toward soft and
  rounded. Under target, so watched, not fixed.
- content-01: SEO description over 160 characters in one run (issue 30, same class as issue 28).
- Reference measurement is flaky on plain sites (ref-01 Craigslist); it falls back to the preset, by design. The
  extractor still needs hand-tuning on ~15 labelled sites (plan section 5).
- Visual side-by-side test of 8 built sites waits on the Group 3 builders.

---

## 2026-11-14 · Evaluation before Group 3, reference fix

**What** Evaluation run 7 (81 runs) with a new "style reference" group (ref-01..03 in `scripts/eval_briefs.json`:
café briefs pointing at craigslist.org, linear.app, stripe.com). The reference did not shape the plan, so:
`reference_style` now measures `corners` from every button; `brief.style_reference` carries it; the planner prompt
names it; `assemble._follow_reference` applies it in code (D-238). Run 8 tried business-type examples in the
direction guidance; it made no difference and was reverted.

**Why** Group 3's builders turn plans into code, so the plans were measured first (D-237 had not been measured).

**Checked** Tests: everything passes except the 62 that need the test database (down). New tests: corners from
unfilled buttons; reference corners win over the model. Runs 7–8: 98.7% and 97.7% correct leaving out network drops.

**Open**
- Live check of D-238: the network dropped site reads during the re-runs, so no run reached planning with a reference.
- KI-29 without a reference: 70–74% direction sameness; prompt wording does not move it (issue 27).
- personal-02: search title over 60 characters in 1 run of 3 (issue 28). forms-03 still plans a contact form.
- The runner counts network drops as wrong plans (issue 29).

**Docs** New `docs/problem-journal.md`: every issue 1–29 worked through step by step (symptom, each try and what
it showed, fix, check, status) and the lessons learned; linked from `README.md` and `progress.md`.

---

## 2026-11-14 · Phase 3 Group 2: plan upgrades

**What** Group 2 of `D:/FYP/reports/FORGE Phase 3 builder plan.md`.
- **2.1 Variants** (D-224): `variant` on 12 components (Hero 4, About, Testimonials, CTA, Services, Features,
  Gallery, Contact, FAQ 3 each; Team, Pricing, Footer 2 each); all 49 components type-check; Needs List regenerated.
- **2.2 Design direction** (D-224): `DesignDirection` in the plan, chosen in the site-design call; mapped to CSS in
  `site_template/app/direction.css` by data attributes on `<body>` (spacing, corners and type are Tailwind 4
  variables, so no component code); hero and footer variants come from it. Checked in the browser with two
  directions (computed styles: spacing, radius, type size, surfaces, alternating bands, heading accents, layouts).
- **2.3–2.4 Showcase sections and variety** (D-224): `showcase` reason on a section (at most 2); code switches the
  variant of a section that would repeat its neighbour's layout family; check 19 flags an unchosen direction or too
  many showcases.
- **2.5–2.6 Custom parts** (KI-07 fixed, D-228): a custom spec lists the fields it `sends` and becomes a form; its
  file path and export name are fixed by code (`components/custom/<id>/<id>.tsx`).
- **2.7 Sample content** (D-225): an obvious sample for every business-details field in the plan.
- **2.8 Sameness score** in `run_eval.py` and evaluation run 6.

**Why** Plans must carry the creative choices and the full contract the builders will execute.

**Checked** 435 tests pass (database tests not run); evaluation run 6: 98.6% correct; one failure fixed after the
run (search descriptions now required text). Variants cut section sameness by about a quarter.

**Open**
- **KI-29** (the model picks nearly the same design direction for every site, 83% match between different
  businesses) decided the same day → **D-237**: the brief carries the user's style reference (website or
  screenshot), and the site-design call designs the direction from it first.
- forms-03 still plans a contact form where lead capture was expected.

---

## 2026-11-14 · Phase 3 Group 1: groundwork

**What** Group 1 of `D:/FYP/reports/FORGE Phase 3 builder plan.md`, approved the same day.
- **1.1 Spike.** Server: the site template with all 49 catalogue components type-checks in 7.5 s and builds with
  Turbopack in 40 s (about 48 s together, under the 60 s target). Browser: WebContainers never finished installing
  Next.js in the app's built-in browser; in Chrome it booted in 10 s, installed in 74 s, served the page at 90 s and
  rendered correctly with `next dev --webpack`. An exported package snapshot is 290 MB (64 MB compressed) and must be
  made inside a WebContainer. → D-232 stands.
- **1.2 Site template** (`site_template/`) → **D-235**: Next.js 16.4.6, Tailwind 4 through PostCSS, the 9 shadcn
  parts the catalogue imports, `lib/utils.ts`, `lib/store.ts` skeleton, default theme tokens, a sample page.
- **1.3 Package cache**: the template's `node_modules` installed once (a fresh install took 2 minutes); every build
  links it.
- **1.4 Build worker** (`agents/build_worker.py`) → D-231: folder per build, catalogue copied in, shared packages
  linked, protected template and catalogue files, no secrets in the environment, time limit with process-tree kill,
  tool errors parsed into file, line and message, a queue (2 at once, one per user).
- **1.5 File store** → D-234, **D-236**: table `generated_files` (migration 0008), memory and PostgreSQL stores,
  manifest in `FileRef` (new `written_by`).
- **1.6 Background builds** → D-233: graph step `build_site` (saves the approved plan as `forge/plan.json` and sends
  progress until the builders exist); approving the plan starts the run in the background; `GET .../events` streams
  progress; the studio shows the lines; a build cut off by a restart starts again at start-up.
- **1.7 Gateway for code** → D-228: `call_files` (`<file path>` blocks, one corrective retry) and
  `call_files_parallel` (at most 3, the budget counts calls still running).
- **1.8 Embeds** → KI-17 fixed: allow-lists in `VideoSection` and `LocationMap`.
- **1.9** Stack decision logged (D-235); AWS reminder set for 2026-12-01.

**Why** The builders (Group 3) need a template, a place to build, a place to keep files and a way to run long jobs.

**Checked** 424 tests pass (new: build worker 9 incl. a real full build, file store, events, gateway file mode and
parallel budget, full run through the build step); database tests not run (test database down). Frontend type check
and lint pass. Spike measured in Chrome.

**Open**
- Migration 0008 applied to the app database (2026-11-14); try plan approval live in the studio.
- FORGE's studio upgraded to Next.js 16.4.6 the same day (KI-26 fixed).
- Measure preview start-up from the package snapshot (Group 3, item 3.7).
- Group 2 (plan upgrades) next.

---

## 2026-11-14 · Phase 3 plan (builders), research only

**What** A full Phase 3 plan in `D:/FYP/reports/FORGE Phase 3 builder plan.md`: 15 problems, each with the evidence, the options and the choice; work order
(Group 1 groundwork, Group 2 plan upgrades, Group 3 builders
later). Decisions **D-224 to D-234** logged as Proposed. Progress log added (`docs/progress.md`, a97f31c).

**Why** The team asked for the problems, the possible solutions and the chosen ones before any builder is written,
and raised a concern that building by code makes sites look alike.

**Found by the research**
- Next.js 16 builds with Turbopack by default, and Turbopack does not run on WebAssembly, so the WebContainers preview
  must use `--webpack` (KI-24); WebContainers needs a commercial licence for for-profit production (KI-25).
- Only 13 of the 49 components have any layout setting; 2026 studies find model-made UIs converge, so variety must be
  designed in (D-224).

**Changed in review with the team (same day)**
- Per-site key: the generated site's backend calls FORGE with a secret key kept on its server; FORGE stores only the
  hash, accepts submissions only for that project, rate-limits per site; the preview has no key (D-227).
- Custom parts written in parallel, at most 3 at a time, instead of one after another: style consistency comes from
  the shared design direction and tokens (D-228).
- Up to 4 fix rounds instead of 2; code applies the compiler's single suggested fix first; a part that still fails
  falls back to a catalogue section (D-230).
- Preview: one package snapshot served as a static file, prefetched in the background when the user confirms the
  brief (not at login; skipped in data-saving mode) (D-232).
- Parked for later research: a tool-using (MCP-style) fix agent, once the build gate works.

- Work order regrouped into three groups (Group 1 groundwork, Group 2 plan upgrades, Group 3 builders); every
  problem P1–P15 and decision D-224 – D-234 is mapped to an item, with a list of what is not in Phase 3.

Plan saved as Markdown and PDF: `D:/FYP/reports/FORGE Phase 3 builder plan.md` / `.pdf`.

**Open** Approval of D-224 – D-234; then Group 1 item 1.1, the spike that decides whether WebContainers can run the preview.

---

## 2026-11-13 · Phase 2: raise brief and plan quality

**What** Phase 2 of the roadmap in `D:/FYP/reports/FORGE architecture lessons from peers.md`, plus the four issues the
baseline found. The team decided sites are English only, so the planned site-language field was dropped.
- **Defaults instead of FAILED** → **D-219** (supersedes D-112): `slots.apply_defaults`.
- **Patch-only fix rounds and section-scoped changes** → **D-220**: `PlanPatch`, `assemble.apply_patch`; texts of
  unchanged sections kept after a change; a change whose text fails is undone.
- **SEO head on every page, a 404 page, checks 17 and 18, accessibility rules** → **D-221**.
- **Audience, content notes and style notes in the brief; English-only copy** → **D-222**.
- **Hero relevance never ends planning; plural stems; button names; link names; output-token cap** → **D-223**
  (KI-20 to KI-23).
- Assumptions on the plan screen now include the brief's (the "You decide" choices and the new defaults).

**Why** Planning used to fail on recoverable gaps and on one strict text rule, regenerate whole plans to fix one
item, rewrite all copy for one change, and leave SEO and accessibility to chance.

**Checked** 20 new tests; 405 pass (database tests not run: test database down). Evaluation re-run on Gemini, same
24 briefs x 3 (`scripts/runs/eval_vertex_20261113_193151.json`):

| Gemini, 72 runs each (24 briefs x 3) | Baseline (after Phase 1) | After Phase 2 |
|---|---|---|
| Correct outcome | 93.1% | **100%** |
| Valid plans | 92.4% | **100%** |
| Must-feature coverage | 92.0% | **97.8%** |
| Questions per run | 0.57 | 0.46 |
| Fix rounds per run | 0 | 0 |
| Model calls per run | 7.8 | 7.75 |
| Cost per run (total) | $0.027 ($1.97) | $0.030 ($2.18), the extra search titles and descriptions |
| Time per run | 47 s | 51 s |
| Failures | 5 (hero relevance rule) | 0; the only miss: forms-03 plans a contact form instead of the lead-capture form, 3 of 3 runs |

**Open**
- forms-03: the plan uses the contact form where the brief expected lead capture (planner choice or expectation; look
  at it with the brief owner).
- Phase 3 (builders) next. Raised while discussing it: building sites by code from the plan risks look-alike sites
  (SL-13); proposal to add component variants and a model-chosen design direction to the plan before the builders.

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
