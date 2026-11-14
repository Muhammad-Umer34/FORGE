# FORGE known issues

Open bugs (code that does not do what its design says) and scope limits (rules that work but narrow what
FORGE can build). When an item is fixed, set its status to **Fixed** with the commit and decision, and
add a work-log entry. Items are never deleted.

Source of the first list: the audit of 2026-11-08, `D:/FYP/reports/FORGE agent scope review.md`
(evidence, file:line and suggested fix for every item; notes in
`D:/FYP/research_notes/FORGE agent scope review/`). Agent: Clar = Clarification, Plan = Planning,
Retr = Context Retrieval.

## Bugs

| ID | Bug | Agent | Severity | Status |
|---|---|---|---|---|
| KI-01 | The grounding "safety net" matches short brand names as substrings, so "Open job positions" becomes POS/ERP, "Daily soups special" courier, "Striped kurta range" payments (`grounding.py:67-73, 126-127`) | Clar | High | Fixed, see below |
| KI-02 | Unrelated owner lists merge into one form field: testimonials, FAQ, gallery, menu, timeline and order form all become `items`; `categories`, `features` collide; before/after slider images share `photos` (`content_schema.py:38-41, 71-81`) | Plan | High | Fixed, see below |
| KI-03 | A required text the model skips never reaches the rewrite round, so planning fails (`texts.py:56-57`, `planning/nodes.py:232, 262-265`) | Plan | High | Fixed, see below |
| KI-04 | Detailed briefs need more tests than the fixed cap of 15 (one per must feature plus one per form); the run fails or a required test is trimmed (`acceptance.py:29-44`) | Clar | High | Fixed, see below |
| KI-05 | Ticking a page-adding extra (FAQ, legal) at the 10-page cap fails the run after confirmation (`grounding.py:220-240`, `clarification/nodes.py:407-414`) | Clar | High | Fixed, see below |
| KI-06 | Urdu, Arabic or emoji custom features all get the id `custom-item`; the second is dropped, then confirm fails (`brief.py:29-30`) | Clar | High | Fixed, see below |
| KI-07 | Custom parts can never get a data model or API: only catalogue `onSubmit` components count as forms (`assemble.py` `form_sections`) | Plan | High | Open |
| KI-08 | Refusal path drops what it promises: `partial` tier never loaded; non-core refusals promise a link button that never enters the brief; a capability beats a valid feature (`catalogue.py`, `slots.py:189-195`, `grounding.py:111-117`) | Clar | Medium | Open |
| KI-09 | `brief.audience` is never filled, yet Planning uses it for copy and the hero relevance rule | Clar→Plan | Medium | Fixed, see below |
| KI-10 | Emails and bare domains in the prompt (`info@x.pk`, "Daraz.pk store") become style references read by Playwright (`reference_style.py:34`) | Clar | Medium | Open |
| KI-11 | Data links are kept only one level deep (booking → class → trainer loses `trainers`), so check 9 fails every round (`assemble.complete_data`) | Plan | Medium | Fixed, see below |
| KI-12 | A user's plan change rewrites all copy without the change text, and a text-stage failure after a change ends the run | Plan | Medium | Fixed, see below |
| KI-13 | Custom features cannot be removed with Edit (`clarification/nodes.py:393-399`, `brief.py:48-52`) | Clar | Medium | Open |
| KI-14 | Code-fixable plan faults waste fix rounds: section/footer/spec page ids not lower-cased; code-added `/blog/[slug]` counts toward the page cap; data prompt never asks for `feature_ids` | Plan | Medium | Fixed, see below |
| KI-15 | Retrieval offers page layouts and site-wide parts as sections ("Live chat" → WhatsApp button); weak plural handling; one generic word is enough to match (`ranker.py:25-32, 46-50`) | Retr | Medium | Open |
| KI-16 | Copy rules misfire on buttons: "Let's talk", cookie "Accept"/"Decline", "Donate", "Enroll" fail the verb check (`texts.py`) | Plan | Medium-Low | Fixed, see below |
| KI-17 | `LocationMap` and `VideoSection` embed any host (no allowlist, no sandbox) | Components | Low-Medium (security) | Fixed, see below |
| KI-18 | Small tidy-ups: `ConfirmationState.decision` lacks `theme_source`; `repairs_used` not reset after edit; unused custom specs count toward the limit; routes keep spaces; `SettingOut.value` only accepts strings; dead `VectorSearcher` | Several | Low | Open |
| KI-19 | The worse-fix guard (D-211) compares only the number of problems, so a fix that swaps one failure for a different one is accepted; it should require strict improvement and no newly failing check | Plan | Medium | Fixed, see below |
| KI-20 | The hero relevance rule fails good headlines: no stemming ("classes" is cut to "clas"), and vague briefs give few business words; all 5 Gemini baseline failures (vague-02 x3, scope-03, personal-03) | Plan | High | Fixed, see below |
| KI-21 | Any text input whose name contains "cta" is treated as a button, so a paragraph such as `cta_body` fails "a button must start with a verb" (`texts.is_button`) | Plan | Medium | Fixed, see below |
| KI-22 | Data links written as `service_id -> services` (MiMo) are not reduced to the entity name, so check 9 fails every fix round; code could normalise them | Plan | Medium | Fixed, see below |
| KI-23 | No limit on output tokens: one OpenRouter reply ran to 131,072 tokens and failed; set a maximum per task in the gateway | Gateway | Medium | Fixed, see below |

| KI-24 | Next.js 16 uses Turbopack by default, which does not run on WebContainers' WebAssembly bindings: the preview must use `next dev --webpack`, and webpack is deprecated in Next.js 16 (D-232). Spike 2026-11-14: `--webpack` works in Chrome | Preview | Medium | Open |
| KI-25 | WebContainers needs a commercial licence for for-profit production use (price on request); free for prototyping and the FYP (D-232) | Preview | Low now, High at launch | Open |

| KI-26 | FORGE's own studio (`frontend/`) runs Next.js 16.4.0, which Next.js reports as having a known security vulnerability (fixed in 16.4.6; the site template already uses 16.4.6) | Studio | High | Open |
| KI-27 | Installing packages inside WebContainers never finished in the Claude app's built-in browser (Chrome works): previews must be tested in a normal browser | Preview (dev only) | Low | Open |
| KI-28 | Migration 0008 (`generated_files`) was not applied to the app database; the build step needs it before plan approval works in the studio | Build | High until applied | Fixed (applied 2026-11-14) |

## Scope limits

| ID | Limit | Decided or accidental | Status |
|---|---|---|---|
| SL-01 | Links to outside services (payment link, Calendly, Foodpanda, tickets, Daraz/Shopify, Google review link) are refused as integrations; existing components already accept links | Partly D-136; unlisted-integration rule accidental | Open (needs a D-decision) |
| SL-02 | One failed required text ends planning; all digits banned ("24/7", "3D"); single-word claim lists; relevance rule without stemming | D-205; word lists accidental | Open |
| SL-03 | Pages come from a closed list of 16 kinds (no Admissions, Courses, Careers); custom features have no page and only a short label | Accidental | Open |
| SL-04 | Recoverable situations end as FAILED (ambiguity after 4 questions, ambiguous edits) | Partly D-104 | Fixed, see below |
| SL-05 | Front-end-only features refused: countdown, analytics, several branches, 360 tour, live-stream embed | Accidental | Open (needs a D-decision) |
| SL-06 | Language, content wishes and style notes never reach Planning; no language or RTL field in brief or plan | Accidental | Fixed, see below |
| SL-07 | Build Plan has no SEO head, 404 page, menu labels, missing-photo rule or accessibility requirement | Accidental | Fixed, see below |
| SL-08 | Per-item pages exist only for the blog (no product, portfolio or event detail pages) | Accidental | Open |
| SL-09 | Catalogued features are locked to their own components (cannot go custom) | Plan v2 checks | Open |
| SL-10 | Check 13 forces "should" features with tests into the plan, against the prompt | Accidental | Open |
| SL-11 | Tight limits: 10 API routes, 1 plan change (page limit removed by D-212); prompts over 2,000 characters cut silently | Placeholders (D-135, D-196) | Open |
| SL-12 | The off-topic rule can refuse websites about academic subjects (maths tuition) | Accidental wording | Open |
| SL-13 | Sites look structurally the same: few layout options, Latin-only fonts, no RTL | Partly D-166 | Open |
| SL-14 | Wording and baselines assume a business; refusal reasons contain draft notes ("Confirm …") | Accidental | Open |
| SL-15 | Revisions (D-124) not built; Project Context §2 still says four site types, against D-134 | Known | Open |

## Fixed

| ID | Issue | Fixed by | Status |
|---|---|---|---|
| FX-01 | Planning counted the run's model calls twice (the subgraph returned the whole usage total) | Planning input schema without `usage` (D-206) | Fixed (b04c43b) |
| FX-02 | A 409 after a restart showed an error under a stale confirmation screen | D-207 | Fixed (d782331) |
| FX-03 | Browser-extension attributes on `<body>` raised a hydration error | D-208 | Fixed (d782331) |
| FX-04 | Home planned at `/home` failed planning even after fix rounds | D-210 | Fixed (f06eda9) |
| FX-05 | Incomplete data contracts (empty `used_by`, feature ids, missing form rules) failed good plans; Flash fix rounds made plans worse | D-209, D-211 | Fixed (f06eda9) |
| KI-01 | The grounding "safety net" matches short brand names as substrings, so "Open job positions" becomes POS/ERP, "Daily soups special" courier, "Striped kurta range" payments (`grounding.py:67-73, 126-127`) | Whole-word matching; short all-caps names only in capitals (`grounding._phrase_in`) | Fixed (Phase 0, 2026-11-13) |
| KI-02 | Unrelated owner lists merge into one form field: testimonials, FAQ, gallery, menu, timeline and order form all become `items`; `categories`, `features` collide; before/after slider images share `photos` (`content_schema.py:38-41, 71-81`) | D-213 | Fixed (Phase 0, 2026-11-13) |
| KI-03 | A required text the model skips never reaches the rewrite round, so planning fails (`texts.py:56-57`, `planning/nodes.py:232, 262-265`) | Required texts left empty go to the rewrite round (`texts.text_problems`) | Fixed (Phase 0, 2026-11-13) |
| KI-04 | Detailed briefs need more tests than the fixed cap of 15 (one per must feature plus one per form); the run fails or a required test is trimmed (`acceptance.py:29-44`) | D-212 (no test cap) | Fixed (Phase 0, 2026-11-13) |
| KI-05 | Ticking a page-adding extra (FAQ, legal) at the 10-page cap fails the run after confirmation (`grounding.py:220-240`, `clarification/nodes.py:407-414`) | D-212 (no page limit) | Fixed (Phase 0, 2026-11-13) |
| KI-06 | Urdu, Arabic or emoji custom features all get the id `custom-item`; the second is dropped, then confirm fails (`brief.py:29-30`) | Custom ids fall back to the item id and never repeat (`brief._custom_id`) | Fixed (Phase 0, 2026-11-13) |
| KI-11 | Data links are kept only one level deep (booking → class → trainer loses `trainers`), so check 9 fails every round (`assemble.complete_data`) | `complete_data` follows data links to the end | Fixed (Phase 0, 2026-11-13) |
| KI-14 | Code-fixable plan faults waste fix rounds: section/footer/spec page ids not lower-cased; code-added `/blog/[slug]` counts toward the page cap; data prompt never asks for `feature_ids` | `tidy` lower-cases section, spec and footer page ids; no page cap (D-212); data prompt asks for `feature_ids` | Fixed (Phase 0, 2026-11-13) |
| KI-16 | Copy rules misfire on buttons: "Let's talk", cookie "Accept"/"Decline", "Donate", "Enroll" fail the verb check (`texts.py`) | Text before an apostrophe is the verb ("Let's" -> let); accept, decline, donate, enroll, register and others added | Fixed (Phase 0, 2026-11-13) |
| KI-19 | The worse-fix guard (D-211) compares only the number of problems, so a fix that swaps one failure for a different one is accepted; it should require strict improvement and no newly failing check | D-214 | Fixed (Phase 0, 2026-11-13) |
| KI-09 | `brief.audience` is never filled, yet Planning uses it for copy and the hero relevance rule | D-222 | Fixed (Phase 2, 2026-11-13) |
| KI-12 | A user's plan change rewrites all copy without the change text, and a text-stage failure after a change ends the run | D-220 | Fixed (Phase 2, 2026-11-13) |
| KI-20 | The hero relevance rule fails good headlines: no stemming ("classes" is cut to "clas"), and vague briefs give few business words; all 5 Gemini baseline failures (vague-02 x3, scope-03, personal-03) | D-223 | Fixed (Phase 2, 2026-11-13) |
| KI-21 | Any text input whose name contains "cta" is treated as a button, so a paragraph such as `cta_body` fails "a button must start with a verb" (`texts.is_button`) | D-223 | Fixed (Phase 2, 2026-11-13) |
| KI-22 | Data links written as `service_id -> services` (MiMo) are not reduced to the entity name, so check 9 fails every fix round; code could normalise them | D-223 | Fixed (Phase 2, 2026-11-13) |
| KI-23 | No limit on output tokens: one OpenRouter reply ran to 131,072 tokens and failed; set a maximum per task in the gateway | D-223 | Fixed (Phase 2, 2026-11-13) |
| SL-04 | Recoverable situations end as FAILED (ambiguity after 4 questions, ambiguous edits) | D-219 | Fixed (Phase 2, 2026-11-13) |
| SL-06 | Language, content wishes and style notes never reach Planning; no language or RTL field in brief or plan | D-222 (audience and notes; sites are English only, no language field) | Fixed (Phase 2, 2026-11-13) |
| SL-07 | Build Plan has no SEO head, 404 page, menu labels, missing-photo rule or accessibility requirement | D-221 | Fixed (Phase 2, 2026-11-13) |
| KI-17 | `LocationMap` and `VideoSection` embed any host (no allowlist, no sandbox) | Allow-lists: video embeds only from YouTube and Vimeo players, maps only from Google Maps embeds; anything else shows the empty state | Fixed (Phase 3 Group 1, 2026-11-14) |
