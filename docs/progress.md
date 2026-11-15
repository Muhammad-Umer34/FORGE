# FORGE progress

How FORGE is getting better, measured: every evaluation run with its numbers and what caused the change, and every
issue met on the way with how it was found and fixed. Updated with every evaluation run and every issue found
(rules in `README.md`). Details: decisions in `decision-log.md`, work in `worklog.md`, open items in `known-issues.md`.

## 1. Scoreboard

The fixed evaluation set (D-217): 27 briefs in 9 groups (simple info site, forms, booking, blog or events, vague,
Roman Urdu, out of scope, personal or non-business, style reference), answered by a strict simulated owner. Early
runs used 24 briefs in 8 groups; the style-reference group was added for D-237/D-239 (2026-11-15). Run count varies
(2 or 3 runs per brief, or a subset). Run with `scripts/run_eval.py`; full per-run results go to `scripts/runs/`
(gitignored, so the numbers are copied into the scoreboard below). The milestone runs behind the before/after story
are kept as files in `docs/eval-runs/`.

- **Correct outcome**: the run ended as the brief expects (a plan, or a polite refusal for out-of-scope requests).
- **Valid plans**: share of the briefs that should be planned that ended with an approved-ready plan.
- **Coverage**: share of the brief's must-have features found in the plan (a failed run counts all as missing).

| # | Date | Code | Models (clarification / planning) | Runs | Correct | Valid plans | Coverage | Fix rounds | Cost per run | Time per run | What changed the numbers |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 2026-11-13 | a6b8e06 (Phase 1) | Gemini 3.8 Flash / 2.5 Pro | 1 | 1/1 | 1/1 | 100% | 0 | $0.030 | 42 s | First live run of the runner (booking-01 only), to measure cost |
| 2 | 2026-11-13 | a6b8e06 | Gemini 3.8 Flash / 2.5 Pro | 72 | 1.4% | – | – | – | – | – | **Not valid**: 71 runs stopped at the first call by a gateway bug (parallel Vertex clients, issue 9 below) |
| 3 | 2026-11-13 | 6e82e0a (baseline) | Gemini 3.8 Flash / 2.5 Pro | 72 | **93.1%** | 92.4% | 92.0% | 0 | $0.027 | 47 s | **Baseline.** All 5 failures: the hero relevance rule (vague-02 ×3, scope-03, personal-03) |
| 4 | 2026-11-13 | 6e82e0a | OpenRouter: GPT-6 Luna / MiMo v2.6 Pro | 72 | 93.1% | 92.4% | 89.9% | 0.28 | $0.009 | 134 s | Provider comparison (D-218). Same correct rate, weaker plans (dropped sections, bad data links), 2.8× slower, 3× cheaper. Gemini kept |
| 5 | 2026-11-13 | 0e8a97f (Phase 2) | Gemini 3.8 Flash / 2.5 Pro | 72 | **100%** | **100%** | **97.8%** | 0 | $0.030 | 51 s | The hero relevance fix (D-223) turned the 5 failed runs into plans; coverage rose because those runs now count. Cost up: search titles and descriptions on every page (D-221). Only miss: forms-03 plans a contact form where lead capture was expected (3 of 3 runs) |
| 6 | 2026-11-14 | Group 2 (uncommitted) | Gemini 3.8 Flash / 2.5 Pro | 72 | 98.6% | 98.5% | 95.7% | 0 | $0.031 | 47 s | Group 2 (variants, design direction, sample content). One failure: a search description left out (check 17), fixed after the run. **Sameness** between plans for different businesses in a group: sections 0.487 (components only) → 0.365 (component + variant); design direction 83% the same (KI-29) |
| 7 | 2026-11-14 | 66387e5 + 3 reference briefs | Gemini 3.8 Flash / 2.5 Pro | 81 | 95.1% | 94.7% | 89.1% | 0 | $0.031 | 63 s | First run with the "style reference" group (ref-01..03: one café brief each, pointing at craigslist.org, linear.app, stripe.com). 3 wrong runs were network drops (forms-02 ×3, 0 calls); without them 98.7%. One real failure: personal-02 search title over 60 characters (issue 28). **Direction sameness** without a reference: 83% → 70%. With different references: 65%, and the references were not followed (issue 26) |
| 8 | 2026-11-14 | 66387e5 + reference fix + guidance trial | Gemini 3.8 Flash / 2.5 Pro | 44 | 97.7% | 97.7% | 94.6% | 0 | $0.034 | – | The 22 no-reference planned briefs ×2, with business-type examples added to the direction guidance. Direction sameness 74% (no better than 70%), rhythm 98% alternating, footer 98% columns; the guidance was reverted (issue 27). Same failure: personal-02 search title over 60 characters |
| 9 | 2026-11-15 | D-239 (uncommitted) | Gemini 3.8 Flash / 2.5 Pro | 54 | 92.6% | 92.0% | 94.2% | 0 | $0.031 | 51 s | **Design variety (D-239): code deals the direction, the model repairs fit.** Direction sameness on the 8 varied choices fell to **44%** (same-family 41%, cross-family 44%), near the ~40% random floor; was ~70% (runs 7–8). Hero split 26% (was 74%), 30 of 36 presets used. 3 of 4 wrong runs were Gemini rate-limit outages (issue 29); real correctness 98.1%. One real failure: content-01 SEO description over 160 characters (issue 30). Reference briefs: 2 of 3 applied and locked their measured choices; ref-01 (Craigslist) could not be measured that run and fell back to its preset (designed). Model edits concentrate on corners (35%) and images (33%), still 74% rounded |

**Sameness** (from run 6): plans for two different briefs in the same group (two booking sites...) compared by
their sections (component + variant, Jaccard) and their design direction (share of equal choices); 0 = nothing alike,
1 = identical.

**Reading the trend.** Run 3 → 5: every gain came from fixing one over-strict code rule, not from a better model or
more model calls (calls per run stayed at 7.8). The other Phase 2 changes (patch-only fixes, defaults when questions
run out, section-scoped changes) protect cases this set rarely triggers, since Gemini needed no fix rounds.

## 2. Issues met and how they were fixed

Newest first. **Found by**: how the issue showed up. Each fix links to its decision. The step-by-step path behind
each row (every try, wrong turns, how it was checked) is in `problem-journal.md`, under the same number.

| # | Date | Issue | Found by | Cause | Fix | Decision |
|---|---|---|---|---|---|---|
| 30 | 2026-11-15 | content-01 ended with an SEO description over 160 characters (1 run) | Evaluation run 9 | Same as issue 28 (title over 60): the rewrite round does not always shorten overlong SEO text | Open (issue 28 class); likely fix: code trims SEO title/description at a word boundary after the rewrite | – |
| 29 | 2026-11-14 | The evaluation counts network drops as wrong plans (forms-02 ×3 in run 7, ref-01 ×2 in the reference re-run) | Run 7: failed runs with 0 model calls | DNS and connection failures (`getaddrinfo failed`, `Server disconnected`) are recorded like planning failures | Open: the runner should mark them as outages and leave them out of the correct rate; the scoreboard gives both numbers until then | – |
| 28 | 2026-11-14 | personal-02 ends with a search title over 60 characters (1 run in 3, runs 7 and 8) | Evaluation runs 7, 8 | The rewrite round asks the model to shorten it and it sometimes does not | Open | – |
| 27 | 2026-11-14 | Without a reference, the model still picks nearly the same direction (70–74% match between different businesses) | Evaluation runs 7, 8 | Prompt wording does not move the model's taste: business-type examples in the guidance made no difference (74%) | Guidance change reverted; needs a team decision (KI-29) | – |
| 26 | 2026-11-14 | A reference site did not shape the direction: Craigslist (square) and Stripe (small corners) became round | Run 7, reference group; traced one run | The summary had no corner reading when a site has no filled buttons, and the model ignored the corners it did get | The reader measures corners on every button (`corners`: sharp, soft, round); code applies them to the direction (square images with sharp corners), like a typed hex code (D-158). Live check pending: the network dropped site reads | D-238 |
| 25 | 2026-11-14 | The model chose nearly the same design direction for every site | Group 2 evaluation, sameness score | Left to choose, the model has one favourite style (the convergence the research predicted) | Team decision: the direction follows the user's style reference when given (website or screenshot); otherwise the model's choice is kept | D-237 |
| 24 | 2026-11-14 | A home page ended without a search description (content-01) | Group 2 evaluation | The description counted as optional text, so one that broke a rule was blanked and check 17 failed | Search titles and descriptions count as required text, so they go to the rewrite round | D-221 |
| 23 | 2026-11-14 | Next.js warned that 16.4.0 has a known security vulnerability | Spike, in the preview's dev server output | Version pinned in October | Site template and FORGE's own studio moved to 16.4.6 (KI-26) | D-235 |
| 22 | 2026-11-14 | The full-run tests broke when the build step was async | Phase 3 tests | Tests run the graph synchronously; an async step needs the async API | The file store and the build step are synchronous (the server runs steps in threads anyway) | D-236 |
| 21 | 2026-11-14 | Installing Next.js inside WebContainers never finished (10+ minutes, three tries) | Spike in the app's built-in browser | The built-in browser, not WebContainers: the same test in Chrome installed in 74 s and served the page at 90 s | Preview stays in WebContainers; tested in Chrome; package snapshot made inside a WebContainer (64 MB compressed) | D-232 (KI-27) |
| 20 | 2026-11-14 | Node crashed at start in the build folder ("CSPRNG assertion failed") | Spike | The worker's no-secrets environment dropped Windows' `SYSTEMROOT` (environment names are upper-case on Windows) | The worker keeps the system variables Node needs and nothing else | D-231 |
| 19 | 2026-11-14 | `next build` refused the shared packages: "symlink target leaves the filesystem root" | Spike | Turbopack does not follow links outside its project root | The worker widens Turbopack's root to the folder holding the build and the template (`FORGE_TURBOPACK_ROOT`, never set on a published site) | D-231 |
| 18 | 2026-11-14 | The 49 catalogue components import 9 shadcn parts that did not exist in the repo | Building the site template | The components were written against shadcn/ui without its files | The 9 parts written into `site_template/components/ui/`; the template type-checks with all 49 components | D-235 |
| 17 | 2026-11-13 | A paragraph input `cta_body` failed "a button must start with a verb" | OpenRouter run (personal-02) | Any input name containing "cta" counted as a button | Only inputs named like a button (`ctaText`, `buttonLabel`) | D-223 (KI-21) |
| 16 | 2026-11-13 | Good plans failed because the hero "did not say what the business offers" | Baseline: all 5 failures | Plurals matched badly ("classes" ≠ "class"); vague briefs gave few business words; one miss ended the run | Plural stems; must-feature names count; after the rewrite a miss becomes a note on the plan screen, not a failure | D-223 (KI-20) |
| 15 | 2026-11-13 | One model reply ran to 131,072 tokens and failed | OpenRouter run | No output-token limit | Every reply capped at 32,768 tokens | D-223 (KI-23) |
| 14 | 2026-11-13 | Data links written as `service_id -> services` failed check 9 every fix round | OpenRouter run (booking-01, booking-02) | MiMo wrote links in its own format | Code reads the entity name from the link | D-223 (KI-22) |
| 13 | 2026-11-13 | MiMo plans dropped must sections and were 2.8× slower | Provider comparison | Model quality | Gemini stays the default; OpenRouter kept as a one-line switch | D-218 |
| 12 | 2026-11-13 | A Phase 2 test fix was rejected by the strict guard | Phase 2 tests | The test's patch added a booking form but not the data it posts to, which is a new failing check: the guard was right | The test patch carries the data too | D-214, D-220 |
| 11 | 2026-11-13 | Code-placed search heads and the 404 page failed check 4 ("not a catalogue component") | Phase 2 tests | `SeoHead` and `NotFoundPage` exist as components but are not in the catalogue | Check 4 accepts the parts code places | D-221 |
| 10 | 2026-11-13 | "menus" was not read as "menu" | Phase 2 spot check | The new plural rule skipped every word ending in "-us" | A short list of real "-us" words instead | D-223 |
| 9 | 2026-11-13 | 71 of 72 evaluation runs failed with "GOOGLE_API_KEY is set" | First full evaluation run | The Google SDK sets `GOOGLE_API_KEY` for a moment while it builds a Vertex client; a parallel run's safety check saw it. Two studio users at once would have hit it too | Clients are built one at a time behind a lock; test with 40 clients from 8 threads | D-218 |
| 8 | 2026-11-13 | The spending cap did not work inside Planning | Phase 1 test | The planning subgraph never receives the run's total (on purpose, see issue 2), so it saw a full budget | The retrieval step hands Planning what was already spent | D-216 |
| 7 | 2026-11-13 | Valid runs ended after confirmation: tests over the cap of 15, extras over the 10-page cap, Urdu or emoji custom features colliding on one id; "Open job positions" read as a POS system; six owner lists merged into one form field | Audit of 2026-11-08 (`known-issues.md`) | Over-strict or imprecise code rules | No page or test cap; whole-word matching; ids from item ids; one form field per component; strict fix guard | D-212 – D-214 |
| 6 | 2026-11-08 | Good first designs failed check 8; Flash fix rounds then wrecked them (one hero section, or no sections) | Live studio runs (bakery, salon) | Data-contract gaps the model left; whole-plan rewrites by a weak model | Code completes the data contract; Pro model for fixes; a fix that adds problems is thrown away | D-209, D-211 |
| 5 | 2026-11-08 | Home planned at `/home`; both fix rounds kept it | Live studio run | The model ignored the located error | Code always puts Home at `/` | D-210 |
| 4 | 2026-11-04 | Hydration error in the studio | User report | A browser extension adds attributes to `<body>` | `suppressHydrationWarning` on `<body>` only | D-208 |
| 3 | 2026-11-04 | "Not waiting for a confirmation" error after a backend restart | User report | The restart cut the run; the screen was stale | The studio reloads the real state after a 409 | D-207 |
| 2 | 2026-11-04 | Model calls counted twice (7 instead of 5) | Phase 5 tests | The planning subgraph returned the whole run's usage total | Planning's input schema leaves `usage` out | D-206 |
| 1 | 2026-10-23 | A crash lost a run, and a second browser could start a competing website | Crash test | Runs lived only in memory | Runs saved in PostgreSQL every step; resume; one website per project | D-197 – D-200 |
