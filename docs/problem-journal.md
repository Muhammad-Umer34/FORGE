# FORGE problem journal

How each problem was worked through, **step by step**, including the wrong turns. `progress.md` section 2 has
the one-line summary of every issue (same numbers); this file keeps the iterations behind it: what we saw, what
we tried, what each try showed, and how the fix was checked. Newest first. Decisions are in `decision-log.md`.

Each entry:
- **Symptom**: what showed up and where.
- **Steps**: each try and what it showed.
- **Fix**: what was changed.
- **Checked**: how we know it works.
- **Status**: fixed, or what is still open.

---

## Lessons so far

1. **Trace before fixing.** Issue 26 was first blamed on the wrong line of code; one traced run showed the real cause.
2. **Measured facts go in code, not in the prompt.** The model ignored a reference's corners (issue 26) and a
   wrong Home route (issue 5) even when told; code applying the fact works every time (D-158, D-210, D-238).
3. **Prompt wording does not change the model's taste.** Business-type examples left the design direction just as
   alike (issue 27). Variety has to come from the user (D-237) or from code.
4. **Keep outages apart from results.** Network drops made runs look wrong (issue 29); check the error before
   counting a failure.
5. **Check the size of a diff.** A 3-brief addition showed as 546 changed lines (issue 26, step 2): the file had
   been rewritten in another format. Small change, small diff.
6. **The environment can be the bug.** WebContainers looked broken until the same test ran in Chrome (issue 21);
   Node crashed because a Windows variable was filtered out (issue 20).

---

## 29. The evaluation counts network drops as wrong plans
**Symptom** Run 7: forms-02 failed 3 of 3 with 0 model calls. Run 7b: ref-01 failed 2 of 3, also with 0 calls.

**Steps**
1. Read the row errors: `ConnectError: [Errno 11001] getaddrinfo failed`. This is a DNS failure, not a planning
   failure; Langfuse could not be reached in the same minutes.
2. Recounted run 7 without them: 98.7% correct instead of 95.1%.
3. Later re-runs also hit `RemoteProtocolError: Server disconnected` (ref-02) and "the website took too long to
   open" when reading Stripe directly.

**Fix** None yet. The scoreboard gives both numbers.

**Status** Open. The runner should mark connection errors as "outage" and leave them out of the correct rate.

## 28. A search title over 60 characters ends a valid run
**Symptom** personal-02 failed check 7 in one run of three, in both run 7 and run 8:
`home.seo.title: longer than 60 characters`.

**Steps**
1. The text check finds it; the rewrite round asks the model to shorten it; the model sometimes returns it still
   too long; the run fails at `finish_texts`.

**Status** Open. A likely fix is code trimming a search title to 60 characters at a word boundary after the
rewrite, the same way code fixes the Home route (issue 5).

## 27. Without a reference, every site still gets nearly the same design direction
**Symptom** Run 6: two different businesses of the same kind matched on 83% of the direction. Footer "columns"
was 100%, rounded images 94%, "calm" type 90%.

**Steps**
1. Run 6 measured it (issue 25). The team decided on D-237: follow the user's reference; otherwise keep the
   model's choice.
2. Run 7 measured the default case again: 70% sameness, better than 83% but still high.
3. Tried one prompt change: business-type examples for every choice (square images for firms, expressive type for
   gyms, a centred footer for one-to-three-page sites, "no choice is a safe default").
4. Run 8 (44 runs): 74% sameness. No better, and rhythm (98% alternating) and footer (98% columns) were still
   fixed. The prompt change was reverted.

5. Asked whether other prompt methods were tried: no. Researched papers and products
   (`D:/FYP/reports/Reducing sameness in AI site designs.md`). The research says prompt-only fixes cannot reach
   the target: a tuned model asked once returns its most typical answer, models fail randomness tests when each
   pick is a separate call, and different models converge too. Products (Squarespace, Durable, Wix, Stitch) all
   pick from designer-curated sets. Verbalized Sampling (the model gives probabilities, code draws) is the one
   prompt method with evidence, but only on text.
6. Discussed the weak point: 4 presets per family still means 2 restaurants share a preset 1 time in 4. Answer:
   presets fix only 4–5 choices and leave the rest open for code to draw; rotation favours the least-used preset;
   the model's 2 changes repair fit; colours, fonts, sections and content differ anyway.
7. Plan approved (D-239, `D:/FYP/reports/FORGE design variety plan.md`), with the research's four changes:
   presets measurably different (≤3 shared fixed choices), presets as ranges, model changes limited to allowed
   ranges with logged reasons, a reference locks its measured choices. Implementation steps follow below.
8. Built `components/design_presets.json` (8 families plus general, 4 presets each, 4–5 fixed choices) and
   `agents/planning/direction.py` (family, seeded pick with rotation, open choices drawn in range, `settle` for
   the model's changes and the footer). The planner deals the start once per site; `build_plan` settles the
   model's direction against it.
9. New problem: planning tests failed with `KeyError: 'request'`, because the planning subgraph's input schema
   did not include the request. Added it; tests that call the subgraph alone seed from the business type.
10. New problem from the new tests: "wedding photographer" was put in events, not creative (one word each, and a
    tie went to the first family listed). Fix: on a tie the later word wins.
11. The 100-site spread test expected presets within 1 of each other; the real spread was 24–26, which is the
    rotation window working. The test now allows a gap of 2. 96 tests pass.
12. Added the reference reader's three new measurements (image corners, section bands, headline size) and the
    variety metrics in `run_eval.py` (same-family vs cross-family match over the 8 varied choices, most-common
    option per choice, model change rate per choice). Live read of the three sites worked: Craigslist sharp,
    Linear square/expressive, Stripe rounded.
13. New problem: a clarification-flow test failed with `JSONDecodeError: Extra data`. The starting-direction block
    sat between "Brief:" and "Placed by code:", and the fake model in the tests slices the prompt between those
    two markers to read the brief JSON, so it caught the extra block. Fix: put the starting-direction block after
    "Placed by code", not before it. All 451 non-database tests pass.
14. New problem: the first full evaluation ran all 54 runs but then crashed in the summary with
    `KeyError: 'footer_variant'`, and the results file was never written, so the run (~$2) was lost. Cause: `shape()`
    leaves footer_variant out of the direction (it is derived from page count), but the new variety loop read it.
    Fix: the loop reads only the 8 varied choices. Also, the runner now writes the rows before computing the
    summary, so a summary bug can never throw away a finished run again.
12. Reference reader: added image corners (big images only, rounding of the image or a clipping parent),
    section bands (each section's background in order) and headline size (main heading vs the most common body
    size). Choices: rounded images from a median of 6 px; alternating when 40% of neighbouring sections change
    background; expressive when the headline is 3.2× body text or more. These thresholds are first guesses
    (marked as a shortcut in the code) until the hand-labelled check.
13. Live read of 4 sites (network back): Craigslist sharp/calm, Linear soft/square images/expressive (dark),
    Stripe soft/rounded/continuous/calm, Duolingo soft/square/alternating/calm. Craigslist and Linear look right;
    Stripe "calm" and Duolingo "square images" are doubtful, to be checked against hand labels.
14. `run_eval.py` now reports sameness over the 8 varied choices (footer left out), same-family vs cross-family
    pairs, the most common share per choice, presets used and the model's changes. On run 8 it gives 0.659 across
    all pairs: the "before" number. Evaluation run 9 started.

**Status** Open (KI-29), being fixed by D-239.

## 26. The user's reference site did not shape the design
**Symptom** Run 7, new "style reference" group: three café briefs pointing at Craigslist (square, plain), Linear
(dark, pill buttons) and Stripe (small corners). Craigslist and Stripe both came out **round**; Linear came out
**sharp**. The opposite of the sites.

**Steps**
1. Added the reference briefs (ref-01..03) to `scripts/eval_briefs.json` as new ids, which the set's rules allow.
   First check: read all four candidate sites with `python -m agents.reference_style`; all four read.
2. First attempt at adding them rewrote the whole file in a different JSON layout (546 changed lines). Restored
   it and appended the three entries in the file's own layout (11 lines). Raised the test's limits to 30 briefs
   and 9 groups.
3. Looked at the planner code and saw `_text_context` passes `style_notes` but not `style_reference`. **Wrong
   lead**: that is the text-writing call. The site-design call uses `_brief_view`, which dumps the whole brief,
   reference included.
4. Traced one run per site (patched the runner to print the frozen brief). The reference did reach the planner
   but only carried `site, feel, dark, heading_font`, with **no corner radius**.
5. Found why: the radius is read only from buttons with a filled background (for the theme). Craigslist's and
   Linear's buttons are text-only or outlined, so there was nothing to read.
6. Fix part 1: the reader also measures `corners` (sharp, soft or round) from every button, pill shapes counting
   as round; the theme keeps its filled-button radius. The brief carries `corners`, and the prompt says to use it
   as given. Test: square text buttons give sharp, pill buttons round, a 4 px filled button soft.
7. Re-ran the reference briefs: Stripe read "soft" and the model **still chose round**. So the prompt is not
   enough.
8. Fix part 2 (D-238): code applies the measured corners to the plan (`assemble._follow_reference`), and sharp
   corners also give square images. The rest of the direction stays the model's. Test: a brief with
   `corners: sharp` gives a sharp plan and keeps the model's hero layout.
9. Live re-run: the brief had **no reference at all**. Reading Stripe directly timed out, so the network had
   dropped the site read (issue 29), not the code.

**Fix** D-238.

**Checked** Unit tests (reader and plan); full suite passes except the 62 tests that need the test database.

**Status** Fixed in code. The live check is still to do, once the network is stable.

## 25. The model chose nearly the same design direction for every site
**Symptom** Group 2 evaluation (run 6), the new sameness score: 83% of the direction was the same between
different businesses.

**Steps**
1. Added the sameness score to `run_eval.py`: sections (component + variant) and direction compared between
   plans of different briefs in the same group.
2. Variants alone cut section sameness from 0.487 to 0.365. The direction, though, stayed nearly fixed.
3. Gave the team three options (code-seeded, per business type, three to pick from). The team chose D-237: the
   user's style reference leads.

**Fix** D-237. Continued in issues 26 and 27.

## 24. A home page ended without a search description
**Symptom** Run 6, content-01: check 17 failed (no search description).

**Steps**
1. The description had broken a text rule, and optional text that breaks a rule is blanked, not rewritten.
2. Search titles and descriptions were counted as optional.

**Fix** They are now required text, so they go to the rewrite round (`texts.required_slots`).

**Checked** Run 7: no check-17 failures in 81 runs.

## 23. Next.js 16.4.0 had a known security vulnerability
**Steps** Seen in the preview's dev-server warning, then confirmed for the pinned version; the site template and
FORGE's own studio were moved to 16.4.6, and both build. **Fix** D-235 (KI-26).

## 22. The full-run tests broke when the build step was async
**Steps** The new `build_site` step was async. The tests run the graph synchronously, so they could not call it.
The server already runs steps in threads, so async gave nothing. **Fix** The file store and the step are
synchronous (D-236).

## 21. Installing Next.js inside WebContainers never finished
**Steps**
1. Three tries in the app's built-in browser, each more than 10 minutes with no end.
2. Same test in Chrome: boot 10 s, install 74 s, page served at 90 s with `next dev --webpack`. So the problem
   was the built-in browser, not WebContainers.
3. The package snapshot (290 MB raw, 64 MB compressed) has to be made inside a WebContainer.

**Fix** The preview stays on WebContainers, tested in Chrome (D-232, KI-27).

## 20. Node crashed at start in the build folder ("CSPRNG assertion failed")
**Steps** The worker strips the environment so no secrets reach a build. On Windows that also removed
`SYSTEMROOT` (names are upper-case there), which Node needs for random numbers. **Fix** The worker keeps the
system variables Node needs and nothing else (D-231).

## 19. `next build` refused the shared packages
**Steps** Builds link to the template's `node_modules` instead of installing. Turbopack refused the link: "symlink
target leaves the filesystem root". **Fix** The worker widens Turbopack's root to the folder holding the build
and the template (`FORGE_TURBOPACK_ROOT`, never set on a published site) (D-231).

## 18. The catalogue imported 9 shadcn parts that did not exist
**Steps** Building the site template, the 49 components failed to type-check: they were written against
shadcn/ui without its files. **Fix** The 9 parts were written into `site_template/components/ui/`; all 49
type-check (D-235).

## 17. A paragraph input `cta_body` failed "a button must start with a verb"
**Steps** Seen in the OpenRouter run (personal-02). Any input name containing "cta" was treated as a button.
**Fix** Only inputs named like a button (`ctaText`, `buttonLabel`) (D-223, KI-21).

## 16. Good plans failed because the hero "did not say what the business offers"
**Steps**
1. Baseline run 3: all 5 failures were this rule.
2. Causes found one by one: plurals matched badly ("classes" did not match "class"); vague briefs gave few
   business words; one miss ended the whole run.
3. Plural stems added; must-feature names count as business words; after the rewrite, a miss becomes a note on
   the plan screen, not a failure.
4. A follow-up spot check found issue 10.

**Fix** D-223 (KI-20). **Checked** Run 5: 100% correct.

## 15. One model reply ran to 131,072 tokens
**Steps** OpenRouter run: no output limit was set. **Fix** Every reply capped at 32,768 tokens (D-223, KI-23).

## 14. Data links written as `service_id -> services` failed check 9 every fix round
**Steps** OpenRouter's MiMo wrote links in its own format and repeated it in every fix round. **Fix** Code reads
the entity name from the link (D-223, KI-22).

## 13. OpenRouter's MiMo dropped must sections and was 2.8× slower
**Steps** Run 4 against run 3: same correct rate, weaker plans, 3× cheaper. **Fix** Gemini stays the default;
OpenRouter is a one-line switch (D-218).

## 12. A Phase 2 test fix was rejected by the strict guard
**Steps** The test's patch added a booking form without the data it posts to, which is a new failing check: the
guard was right. **Fix** The test patch carries the data too (D-214, D-220).

## 11. Search heads and the 404 page failed check 4 ("not a catalogue component")
**Steps** `SeoHead` and `NotFoundPage` are placed by code, not taken from the catalogue. **Fix** Check 4 accepts
parts that code places (D-221).

## 10. "menus" was not read as "menu"
**Steps** Found in a spot check after issue 16's plural rule: the rule skipped every word ending in "-us".
**Fix** A short list of real "-us" words instead (D-223).

## 9. 71 of 72 evaluation runs failed with "GOOGLE_API_KEY is set"
**Steps**
1. Run 2 was invalid: every run but one stopped at the first call.
2. Found that the Google SDK sets `GOOGLE_API_KEY` for a moment while it builds a Vertex client; a parallel run's
   safety check saw it. Two studio users at once would have hit it too.

**Fix** Clients are built one at a time behind a lock (D-218).

**Checked** 40 clients from 8 threads; run 3 valid.

## 8. The spending cap did not work inside Planning
**Steps** A Phase 1 test showed Planning saw a full budget: the planning subgraph never receives the run's total
(on purpose, issue 2). **Fix** The retrieval step hands Planning what was already spent (`spent_before_usd`,
D-216).

## 7. Valid runs ended after confirmation
**Steps** The 2026-11-08 audit listed several causes:
- tests over the cap of 15;
- extras over the 10-page cap;
- Urdu or emoji custom features colliding on one id;
- "Open job positions" read as a POS system;
- six owner lists merged into one form field.

**Fix**
- no page or test cap;
- whole-word matching;
- ids from item ids;
- one form field per component;
- a strict fix guard.

(D-212 to D-214)

## 6. Good first designs failed check 8, then fix rounds wrecked them
**Steps** Live studio runs (bakery, salon) showed two problems:
1. The model left gaps in the data contract.
2. Flash fix rounds rewrote whole plans, leaving one hero section or no sections.

**Fix**
- code completes the data contract;
- the Pro model does fixes;
- a fix that adds problems is thrown away.

(D-209, D-211)

## 5. Home planned at `/home`, and both fix rounds kept it
**Steps** The model was told the exact error and ignored it twice. **Fix** Code always puts Home at `/` (D-210).

## 4. Hydration error in the studio
**Steps** Reported by a user; traced to a browser extension adding attributes to `<body>`.
**Fix** `suppressHydrationWarning` on `<body>` only (D-208).

## 3. "Not waiting for a confirmation" after a backend restart
**Steps** The restart cut the run while the screen still showed the old state. **Fix** After a 409 the studio
reloads the real state (D-207).

## 2. Model calls counted twice (7 instead of 5)
**Steps** The planning subgraph returned the whole run's usage total, which was added again. **Fix** Planning's
input schema leaves `usage` out (D-206).

## 1. A crash lost a run, and a second browser could start a competing website
**Steps** Crash test: runs lived only in memory. **Fix** Runs saved in PostgreSQL every step, resumed at start-up,
one website per project (D-197 to D-200).
