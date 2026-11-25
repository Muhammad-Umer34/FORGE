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

## 34. Forms that really save (the Backend Agent)
**Symptom** The Database Agent gave each site its own tested database, but nothing used it:
- the site's forms saved nothing (KI-30);
- their field names did not match the tables (`fullName` against `client_name`, KI-38);
- the owner could not see a single booking.

**Steps**
1. Umar chose: one code-built form (`DataForm`); sites reach their data only through FORGE with a secret site key;
   a simple owner dashboard. His concern: "every website will have different routes". Answer: FORGE needs a few
   fixed routes for all sites, because each site's `schema.json` (its contract) says what exists, the way Supabase
   or Firebase serve many databases through one API. Plan: `D:\FYP\reports\FORGE Backend Agent plan.md`.
2. Day 1:
   - `site_storage` registry (migration 0009): schema, role, contract and key hashes only;
   - the contract marks visitor fields (not status, not worked-out fields like `end_at`);
   - the data service `backend/services/site_data.py`: values checked against the contract, saved as the site's
     own role, the database's refusals turned into plain messages;
   - routes `POST /api/site-data/{table}`, `GET /api/site-data/{table}` with the key in a header and a per-site
     rate limit;
   - provisioning registers the site and gives the preview a fresh key, kept only in memory.
3. First test run: 11 of 14 passed. Three bugs, all mine:
   - **Friendly messages crashed for "working hours".** The table of messages was built for every rule at once,
     and "within_hours" has a setting also called `hours` that names a table, so it could not become a number.
     Now each message is built only for its own rule.
   - **An order's items were refused** because their link to the order was required before the order existed.
     The link is now set by code and skipped in the check.
   - **A reply field `status` clashed** with the helper's HTTP status argument.

   After the fixes: 14 of 14.

**Checked** 14 tests on the local PostgreSQL:
- a booking is saved as New, even if the visitor sends "Done";
- a double booking gets "That time is already taken";
- notice and closing-time rules come back in plain words;
- every value kind is checked;
- an order and its items are saved together or not at all;
- a full class gives a waitlist place;
- public lists never show personal data or hidden items;
- a wrong or missing key gets 401;
- a site's key cannot reach another site's tables.

Full suite: 679 passed.

4. Day 2:
   - **availability:** free start times from working hours, days off, bookings that still count, the service's
     length and the notice rules; the database still re-checks every booking;
   - **the Backend Agent** (`agents/backend_generator/`, code only) writes `lib/forms.json` (one form spec per
     form section), `lib/schemas.ts` (a strict zod schema per form, in the owner's words) and `api/contract.json`;
   - **site template:** gets the generic route files (`app/api/data/[table]/route.ts`, `.../availability`) and
     `lib/forge.ts`; the old memory store is gone;
   - **the backend gate** runs FORGE's real data service on the site's storage in one rolled-back transaction.

   Route params are a Promise in this Next.js version (read in its bundled docs first, as `AGENTS.md` asks).
5. **Route paths: code owns them now.** The plan's route paths are made the real ones (`/api/data/{table}`; a GET
   on a booking table becomes its availability). 4 planning tests expected the model's paths (`/api/bookings`) and
   were updated.
6. **A plan with no routes had no forms.** The first Backend Agent tests found no forms at all. Cause: a form only
   got a route if the model had written one. Fix: code makes the missing POST route when a recipe table serves
   the form. Children such as order items are excluded because they have no status.
7. **A `consent` tick was going to be refused.** The zod schema sends a `consent` tick, which FORGE would refuse
   as an unknown field. It is now accepted as a form control and never stored.

**Checked** availability test; `tests/test_backend_agent.py`:
- specs for a salon and a bakery;
- strict zod with the owner's labels;
- the generated schemas type-check in a real site build;
- the gate passes on real storage and leaves nothing behind.

Full suite 687 passed.

8. Day 3: `site_template/components/DataForm.tsx`, one form drawn from its spec:
   - every field kind;
   - lists filled from the site's own routes;
   - free-time buttons for booking tables;
   - an order's item rows;
   - the consent box;
   - errors next to the fields and in plain words from the server;
   - labels, `aria-invalid`/`aria-describedby`, focus moved to the result.

   The compiler draws `DataForm` for every form section on a recipe table and writes `lib/schemas.ts`. Old plans
   keep the library forms. A whole salon site with `DataForm` type-checked and built for production first time.

9. Day 4, with Umar's OK:
   - migration 0009 run on Supabase (0008 -> 0009; nothing existing touched);
   - a new local database `forge_sites` for site storage;
   - `.env`: `SITE_DB_URL` and `FORGE_DATABASE=on`;
   - reopening a project now makes a fresh preview key.

   Found on the way: `.env` again had two active `TEST_DATABASE_URL` lines; the local one, in effect, names no
   database, so the tests use the server's default `postgres` database. It works, so it was left alone.
10. **First live build: the database part worked, but no forms.** "Database: 7/7 rule tests passed", then "Backend:
    no forms send anything". The planner had put the appointment slot picker (no submit of its own) on the booking
    page. The booking POST route listed that section, but form detection only counted parts with a submit. Fix:
    any section a recipe table's POST route serves gets `DataForm`. Rebuilt: "Backend: 1 form on 3 routes", "7/7
    checks passed".
11. **Free times stuck on "Looking…"**, then 502. The site's call to FORGE never finished. A direct call hung
    too, but at *connecting to Supabase*: a new connection there took about 7 s. Every site request made two
    Supabase round trips (the key lookup and a rate-limit count), which could pass the site's 10 s timeout; the
    lists only worked on already-open connections. Fix:
    - keys are remembered for a minute;
    - the per-site rate limit is counted in memory (noted as a shortcut);
    - the site waits up to 20 s.
12. **Then "No free times".** The backend's automatic reload after the edit had stopped every preview, and the
    in-memory key went with it. Reopening the project gave a fresh preview and key, and free times appeared.
13. **Live result** (Glow Salon preview, local storage):
    - free times 09:00-17:30 for 2 December;
    - booked 15:00 with "Sample name 2": "Your appointment request has been received.";
    - the row is in `site_<id>.appointments` as New, 15:00-15:30 (end worked out by the database);
    - a second booking at 15:15 gets "That time is already taken. Please pick another." (409);
    - a Sunday booking gets "We're closed at that time..." (409).

    A booking without a phone got zod's own words ("expected string, received undefined"). Fix: the generated
    schemas give every field the owner's wording when it is missing.

14. **The owner's dashboard (day 5, D-250).** Owner-only routes under `/api/projects/{id}/data` and a "Site data"
    page in the studio. The owner routes answer `{ok, message, field}`, which the studio's error reader did not
    know, so every refusal would have read "FORGE returned an error". Fix: the reader also takes a top-level
    `message`.
15. **Live check, two bugs.**
    - The add-stylist form showed two empty dropdowns and no Name box. The contract sends `options: []` for
      plain fields, and an empty list counts as true in JavaScript. Fix: test the list's length.
    - "Remove sample rows" removed nothing. Ayesha's real booking uses a sample stylist and a sample service, so
      those two could not go; the function then raised inside its one transaction, undoing every other delete.
      Fix: a table blocked as a whole is cleared row by row; only rows still in use stay, and the reply says how
      many (new test).
    - The backend's automatic reload did not pick up the fix (it still sent the old message); a restart did, and
      signed the studio out.
16. **Live result** (Glow Salon, local storage):
    - the real booking shows with its stylist and service names; New → Confirmed, after which New is no longer
      offered (Done, Cancelled, No-show are);
    - "Sara Ahmed, Senior stylist" added;
    - "Removed 14 sample rows. 2 stay because your own rows still use them";
    - the site's public stylist list now reads `Sample name 2`, `Sara Ahmed`.

17. **The evaluation's backend stage (day 6).** `run_data_eval.py` now makes each planned site's storage for a
    throwaway project and calls the real site-data routes with its key: the sample submission saved, a wrong key
    refused, one rule-breaking submission refused with the right code. Tried offline on the salon and bakery test
    plans first: 201, 401, 409 "That time is already taken", 422 "Please fill in 'Your name'".
18. **First full run crashed** on the pet groomer: `unsafe identifier 'r_grooming_appointments__end_from_duration'`.
    Plain names may have 41 characters; a rule name joins two of them. Fix: names code builds may run to
    PostgreSQL's 63. The run writes its file only at the end, so it was run again.
19. **D2: 7 of 12 planned; backend 6 of 7 sites, 23 of 24 checks.**
    - **Groomer:** its sample booking (Thursday 13:00) was refused as "closed". PostgreSQL fires triggers in name
      order; FORGE relies on `a_` (work out the end time) before `c_` (check opening hours). A long name was
      shortened to `f_a_...`, which sorts after `c_...`, so the hours check saw no end time. The database gate's
      7/7 missed it because it tries rules one at a time. Fix: no prefix on a valid name. Offline: 3/3. The
      repeat check also "passed" on the closed message; it now passes only after a saved first submission.
    - **Clinic, check 9:** the model's free-times route listed `date` (a query value) as a field. Fix: GET routes
      on recipe tables take no visitor fields (test).
    - **Check 30, four requests:** a detail's words were not found in any field ("number of people" against a
      guests field, "when they need the work done" against a date). Fix rounds did not add a field. Open.

20. **Check 30 by code (D-251, Umar's choice).** A detail no field holds gets an optional text field, labelled with
    the visitor's words ("Number of people"), on the record type their form sends, and the form sends it. Test:
    "number of people" and "pet's breed" added, "phone" not doubled, check 30 clear.
21. **D3: 12 of 12 planned**, 60/60 rule tests, 18/18 owner answers, backend 12/12 sites and 42/42 checks; 48 s
    and $0.015 per request.

**Status** Done: the Backend Agent's six days. Not committed yet.

---

## 33. Sites need complex data the owner can shape (the Database Agent)
**Symptom** The plan's data model was flat. A `choice` field had no options, links were names with no foreign
keys, and rules were free English ("no two bookings for the same slot"). D-227 put every site's data into one
shared JSON table, so nothing could stop a double booking. Umar asked for owners to keep the data their business
really needs, for example appointments with staff, durations, working hours and no double booking, and to be
able to shape it.

**Steps**
1. Read the existing contract: `DataEntity`, `DataField`, 7 `DATA_STARTERS`, checks 8-10, `lib/store.ts` (D-227).
   Seen: the planner already designs entities, routes, form rules and statuses, so the gap is the vocabulary, not
   the pipeline.
2. Umar chose: its own PostgreSQL schema per site; owner control both ways (data questions and a review step);
   all cases (appointments, classes, orders and quotes, catalogues, anything else in scope).
3. Chose the same split that fixed sameness and built the frontend: the model picks recipes and switches from
   menus, and code expands and compiles them. The model never writes SQL (plan:
   `D:\FYP\reports\FORGE Database Agent plan.md`).
4. Day 1, data model v2 (`agents/state.py`):
   - field options, links, on-delete, unique, default, min/max, locked;
   - `DataRule` with 11 rule kinds;
   - `role`, `label`, `pattern` on record types;
   - limits raised (12 record types, 16 routes);
   - `data_choices` on the brief;
   - question kind F.

   A separate `DataFieldType`, so the custom-part props types did not change.
5. Wrote `components/data_patterns.json`: 14 recipes in 6 families with switches and ready-made questions.
   Wrote `agents/planning/data_patterns.py`: expansion with owner answers locked, then the model's values, then
   defaults; renaming record types; rule sentences by code; a check of everything the compiler will rely on.
6. A test expands **every recipe with every combination of switch values** and checks the result. It passed
   first time except one thing: "yoga studio" picked the salon recipe, because "studio" was in the salon's words.
   Fix: drop the generic word.
7. The first rule sentences read badly ("Each class times takes at most its places in people", "Until must be
   after from"). Fix: field labels in quotes, plural labels read as one item, and the start field named in time
   rules. Now: `"Date and time" must be at least 2 hours ahead`.
8. The new check numbers 11-19 clashed with the existing plan checks 1-19, so they became 20-28. One old test
   assumed the 10-route limit, so it was updated to the new 16.

9. Day 2: plan checks 24-28 (personal data, a status on submissions, size, the owner's answers) and a
   `data_recipes` list on the plan, so the answers can be compared with what was planned. They apply only to
   record types from recipes, so plans made before D-242 keep passing.
10. Day 3, data questions (kind F): asked last, at most 3, only while questions are left, with "Let FORGE
    decide". 4 clarification tests failed because they expected the confirmation right after the visitor-actions
    question. The behaviour was intended, so the tests now answer the data questions, and one checks the exact
    questions and the summary line ("How do customers get their order? They pick it up.").
11. Planning call 2 now returns recipes, switch values, renames, extra fields and custom record types. Gemini's
    output schema cannot take free dictionaries, so rule settings became flat optional fields (`DataRuleOut`).
    The fake planner in the tests made record types without a status, and its form fields were camelCase
    (`fullName`), which check 26 refuses. A test helper now makes them like the real model must.
12. A catalogue item's "name" was marked personal (so the menu got a consent box and a dashboard view). Fix:
    names, emails and phones count as personal only on visitor submissions.
13. First live run (6 booking and form requests): 5 of 6 planned. forms-01 failed check 9 twice: the route sent
    `needed_at`, which the planned orders did not have, and 2 fix rounds did not repair it. Fix (model decides,
    code writes): code sets a recipe record type's POST fields (the model's valid ones plus every required one)
    and its GET fields (never personal data). Rerun: 3 of 3 planned, coverage 100%, no fix rounds.
14. Runs took 115-137 s against about 50 s in run 9, with the same calls and output tokens. Two requests that
    store no data took 112 s against 31-49 s. **First (wrong) conclusion:** the provider was slow that day.
    **Corrected on day 7:** the evaluation runner takes its run settings from the API (`_run_config`), and `.env`
    turns on the live preview and the build gate, so since D-240 every evaluated request also started a dev
    server and a production build after approval. With both switched off for evaluations, the same two requests
    took 38 s and 39 s. Lesson 4 again: check what a run actually did before blaming the environment.

15. Day 4, the SQL compiler:
    - every identifier passes the plan-check pattern and is quoted, and every value goes through one `literal`
      function;
    - tables are made first and linked afterwards, so order never matters;
    - each rule becomes a named constraint or trigger raising `FORGE_RULE:<rule_id>`.

    29 unit tests, including hostile names and values, passed first time.
16. Testing on a real database was blocked. Local PostgreSQL needed a password, and FORGE must not enter
    passwords. Umar put a local `TEST_DATABASE_URL` in `.env`; the database did not exist yet. Two active
    `TEST_DATABASE_URL` lines were found: the first still pointed at the deleted Supabase test project. That line
    was commented out, and `forge_test` was created from the new one (`btree_gist` available).
17. With a test database again, the ~60 database tests that had been skipped since the old project was deleted
    ran: 7 failed, none from this work. Since D-233 the API streams the run (`graph.astream`), and the test fakes
    had only `ainvoke`. After that fix, one more failed: approval starts the build in the background, and the
    background step wrote with the app's real database session, not the test one, so the lock stayed held.
    Fixes: the fakes stream; the test harness gives the background step its session (restored after the test);
    the plan test waits for the background build.
18. Day 4-5, the database gate (`gate.py`) on the local database:
    - apply the schema and the sample rows in a scratch schema;
    - try to break every rule;
    - roll back.

    The first run passed 13 of 14 recipes. events failed: the "can't be in the past" test used a time 5
    minutes ahead, which that rule allows. Fix: such rules are tested with yesterday.
19. A test of **every recipe with every combination of switch values** found two gate bugs, not schema bugs:
    - a capacity test's change (capacity lowered to 1) stayed for the next rule's test, because a released
      savepoint keeps its changes;
    - a test copy of a rental overlapped the sample row, so "no double booking" refused it before the date
      check could.

    Fixes: each rule test runs in its own savepoint that is always rolled back, and test copies move a week
    later (same weekday and time) unless the test is about overlaps. Now every rule holds in every combination.
20. A parallel test proved the capacity lock: two bookings sent at the same moment for the last place gave
    exactly one place and one waitlist.
21. Day 5, provisioning: its own schema and a NOLOGIN role per site. A test proved one site's role cannot read
    another site's schema or delete its own rows, and a rebuild keeps real rows (renamed schema, never dropped).
    Site roles from early test runs were left behind (roles belong to the whole server), so `drop` now removes
    the role too.
22. Wiring into the build: a flow test failed because the first progress line is now the Database Agent's
    ("Database: designing 1 tables..."). The test was updated and the plural fixed. A plan from before recipes
    could crash the compiler (a choice with no options), so the agent checks the model first and skips storage
    with a plain message.

**Checked** 29 compiler tests, 17 gate tests on PostgreSQL (all recipes × all switch values), 7 provisioning and
agent tests; the full suite incl. database tests passes (639).

23. Day 6, the review panel "What your site will keep":
    - owner edits are replayed on the planned record types, so undo is "replay all but the last" and edits survive
      a later plain-English change;
    - refused edits come back as the screen's notice;
    - a new edit decision on the plan screen sends the screen back after each edit.

    One existing test expected the old decision shape and was updated (`edit: null`).
24. Live in the studio (Glow Salon):
    - the questions appeared ("Do clients choose who serves them?");
    - "Let FORGE decide" stored nothing, and the two answers showed in the summary;
    - the plan renamed staff to stylists;
    - the panel showed 5 lists and their rules; adding "Hair length" (choice), changing 60 -> 30 days and undoing
      all worked;
    - the build ran the Database Agent first, and its saved `db/` files hold the new column.

    Each edit took about 10 s (the run is saved to Supabase on every step).
25. Seen live and fixed:
    - **Too much was locked.** The "no double booking" rule showed "(your answer)" because it also depends on the
      stylist answer, though the owner let FORGE decide on double booking. Now locked only when every answer
      behind it is the owner's.
    - **Settings lists were editable.** "Working hours" offered "Make optional"; settings lists are filled by FORGE
      and are now not edited field by field.
    - **Rule checkboxes had no name** for screen readers ("on"); they are now named after their rule.

**Checked** 21 data-edit tests; type check and lint of the studio; live run above.

26. Day 7, the data evaluation (12 requests, `scripts/run_data_eval.py`). The first two full runs reported
    "not planned" for every request. The runner guessed an outage, and a debug run did show a real 429 from
    Google, so 2 more runs were made with waits (15 min, then 90 s between requests): still 0 of 12. Comparing
    with a direct step-by-step run that planned fine showed the real cause: the runner stopped at the plan screen
    and read the run's state while the plan was still inside the paused planning step. Fix: read the planning
    step's own state. **Lesson:** a guess written into an error message ("outage") hid a bug for three runs.
27. D1 result:
    - 11 of 12 planned;
    - on all 11 the schema applied and 50 of 50 rule tests passed;
    - 17 of 17 owner answers kept;
    - 100% must-have coverage;
    - 49 s and $0.017 per request; the gate took 0.3 s.

    The pet groomer failed check 29 twice: the model added the catalogue recipe renamed "services" beside
    appointments' own services. Fix (in code, not only the prompt): a clashing catalogue list gives way to the
    other recipe's list, plus one prompt line. The rerun of that request first hit a real Google rate limit,
    right after the 12-request run.

28. The pet groomer rerun planned (the clash fix worked; 7 of 7 rule tests), but only 1 of its 3 must-haves was
    there: no field for the pet's name, breed or age. A debug run printed what the planner was told: the brief
    had no trace of them (no content notes, nothing on the booking feature). **The detail was lost in
    clarification, not in planning.** Fix (D-246):
    - the first reading of the request also lists the details visitors must give (`visitor_details`);
    - they go into the brief and its summary ("Visitors also tell you: pet's name, breed, age.");
    - the planner is told to give each one a field;
    - plan check 30 refuses a plan where any of them has no field (matching every word of the detail against a
      field read with its record type, so "name" on `pets` holds "pet's name" but `client_name` does not).

    Live rerun: the brief carried the 3 details and the plan added `pet_name`, `breed` and `age` to the
    appointments, with no fix round.

**Status** Days 1-7 done; the full data set is being rerun with the fix.
- Not yet tried on Supabase: `btree_gist` and `CREATE ROLE` there (KI-35).
- Edits take about 10 s each (KI-39).
- Next: the Backend Agent (forms to routes, KI-38).

---

## 32. Custom parts written by the model (the rest of the Frontend Agent)
**Symptom** The Frontend Agent compiled library parts by code, but every custom part (a feature our library cannot
build) and showcase section showed a plain placeholder section. The report's Chapter 7 must describe the agent as
built, and Chapter 9 needs real builder numbers.

**Steps**
1. Planned it (`C:/Users/umerc/.claude/plans/greedy-crafting-kurzweil.md`, approved): writer (D-228),
   post-processors (D-229), gate with fix rounds (D-230), builder evaluation (Phase 3 item 3.8).
2. Compiler: takes the written parts (section id → module, export name) and imports them with the props it already
   builds; a missing part keeps its fallback. Old compiler tests still pass.
3. Writer (`custom_writer.py`): code writes the props interface from the part's needs (all optional, so a missing
   sample never breaks the build) and renders each prompt from the plan: spec, props, sample props, design
   direction, a library section from the same page as a style reference, the real export list of the 9 interface
   parts. A reply is accepted only inside the part's own folder and with the right export. Gateway tasks
   `frontend_custom` and `frontend_fix` default to the planning model (gemini-2.5-pro).
4. Post-processors (`postprocess.py`): imports, icons (3,756 real names read from the installed package), colours,
   paths. While writing them, found that a renamed icon could end up imported twice (a TypeScript error); the lucide
   import line is now de-duplicated. 4 seeded-mistake tests and 4 contract tests pass first time.
5. Gate (`gate.py`): errors are attributed to the part that caused them (in its folder, or a page line that uses
   it), code fixes "Did you mean" errors first, then one model fix round for every failing part, checked by one build;
   a fix that does not lower that part's error count is thrown away; after 4 rounds the part falls back.
   Self-review before testing found two weaknesses: each round built twice (a trial build, then the same build
   again, about 30 s wasted) and code fixes had no limit (they could cycle). Fixed: one build per round, its result
   reused, code fixes capped. 5 tests with fake builds and a fake model pass.
6. Wired into the agent: model code only enters a site through the gate (gate off in tests: no model call);
   model-written files are stored as written by the model; the run's cost now includes the parts (`build_site` gives
   the agent `budget_left`, returns the usage). All 474 fast tests pass.
7. First live test (`b-rest-02`, a cafe with a digital loyalty stamp card): the site built first time, but with no
   custom part at all. Cause: clarification correctly ruled the card unsupported, because tracking each customer's
   stamps needs customer accounts, which FORGE does not build; it went to "not built" with an alternative. The test
   request was the problem, not the code. Kept as a refusal case (requests are never edited once they have results)
   and added `b-rest-03`: a build-your-own-coffee price tool, which works inside the page.
8. The four custom requests: 3 custom parts (price calculator, fee estimator, delivery-zone checker) written by the
   model, all passing the type check and production build first time, about $0.004 each. `b-rest-03`'s coffee tool
   was matched to the library's product-detail part (option pickers with a price), so it needed no custom code.
9. Looked at the result, not just the numbers. The price calculator rendered, but its samples were useless:
   "Service 1 service_name" and every price "Rs. 0", so a working calculator always totalled 0. Fix: rising round
   amounts (Rs. 1,000, 2,000, 3,000) for price-like fields, still under the sample banner, and "Service 1" for name
   fields. All 49 library parts still type-check.
10. **New problem while re-testing:** the demo crashed with `FileExistsError`: an earlier demo process still held
    the same preview folder name. Fix: every preview start gets its own folder.
11. **Found by trying it in the browser:** the calculator worked with a mouse (Service 1 + Service 3 = Rs. 4,000),
    but its rows were clickable `<div>`s that a keyboard cannot reach (`tabIndex` -1). Digging further showed a gap
    in my own wiring: the agent threw away the post-processors' issues, so raw colours or bad imports were only
    fixed if they happened to break the build. Fixes: a new check reports clickable divs; the gate gets a
    "code checks" layer before the type check, which sends those issues to at most 2 fix rounds (a fix is kept only
    if it lowers the count; these issues never drop a part, because the part still works); the writer's rules now
    name the button rule. 4 new tests pass.

12. Full builder evaluation (9 requests): all 9 sites built first time, none failed; 3 of 3 custom parts in
    their sites; 97% of files written by code; 34 s and $0.0016 of model cost per site on average. Checked the parts
    themselves: the calculator now uses real checkboxes, the fee estimator a labelled select, and no part has a
    post-processor issue. Fix rounds and fallbacks were not needed, so they are verified only by tests (KI-34).

**Status** Built: custom parts are written by the model and checked by the gate. Open: harder custom requests to
exercise the fix rounds live (KI-34).

## 31. The frontend agent (building the site from the plan)
**Symptom** Approving a plan saved `forge/plan.json` and stopped: every builder was an empty stub. The supervisor
demo (2026-11-16) needs one live run from request to a running site.

**Steps**
1. Planned the frontend agent alone (backend and database wait), as a code compiler (D-240,
   `C:/Users/umerc/.claude/plans/greedy-crafting-kurzweil.md`). Read the inputs first: the plan's pages and sections,
   texts keyed `section.prop`, sample content keyed by `section_keys`, the theme's tokens and fonts (the test plan's
   theme has no fonts or radius, so the compiler needs defaults), and the need kinds per component: copy 162,
   setting 50, code 77, list 34, fact 38, live 14, image 8.
2. Found that forms already show their success message without a handler (so they work with no backend), that
   components use plain `<img>` (stock photo URLs need no config), and that the template has no `public/` folder.
3. Chose `next dev` on the server for the live preview (its WebSocket updates the open page as files are written),
   not WebContainers yet (90 s boot, Chrome only).
4. Listed every required input of the 49 components and every input with a structured type. The plan's sample
   content gives plain strings for 11 structured types with no item fields in the Needs List (opening hours, social
   links, blog posts, events, the slot picker's availability...). Read their shapes from the component files and
   made a sampler per shape.
5. Wrote `agents/frontend_generator/compiler.py` and `photos.py`; the old stubs (`generator.py`, `scaffold.py`)
   were deleted (nothing imported them). The salon test plan compiles to 10 files.
6. Safety net: `tests/test_frontend_typecheck.py` renders all 49 components on one page with compiler-made props
   and runs the real type check. First run: 2 of 49 failed.
   - PricingTable: `onCtaClick` is a function inside each plan item, and the compiler gave it a string. Fix: leave
     out function fields inside items, like top-level handlers.
   - ImageTextRows: `actionLink` is a nested `{label, href}` object, but the Needs List flattens it into three
     sibling fields. Fix: the fields after a `{` field are built inside it.
7. Second run: crashed, because the sample gave `actionLink` as a string. Fix: a nested value is used only if it
   is an object.
8. Third run: ProcessSteps failed, `stepNumber` missing. Step 6's fix had skipped every code field inside items,
   but `stepNumber` is a required code field that is not a function. Fix: skip only functions. Fourth run: all 49
   components pass the type check.
9. Stock photos: collecting photo ids from Unsplash's website pages was not the right way; the proper route is the
   official Unsplash API with a developer key the owner creates. Until then images are theme-tinted placeholders
   (`photos.placeholder`), which the dealer already falls back to.
10. Wrote the run (`agent.py`: input summary, compile, file store, preview, gate), the preview manager (`preview.py`:
    `next dev --webpack` in a worker folder, output drained in a thread so a full pipe never stops it, one preview
    at a time) and `scripts/frontend_demo.py`. Preview and gate are switched by the run's config (`RunConfig.preview`,
    `build_gate`, from `FORGE_PREVIEW` / `FORGE_BUILD_GATE`), off by default so tests never start dev servers.
    One old test expected the old first message; updated to the new events.
11. First live run (booking-01, a hair salon): plan, 11 files, preview up, pages written one by one, the page
    looked right (theme, Playfair Display headings, full-bleed hero from the glossy-studio preset). **New problem:**
    the gate's type check failed on FeaturesGrid: the planner wrote `columns: "3"` where the type is `2 | 3 | 4`. The
    dev server does not type-check, so only the gate caught it. The all-components test missed it because it had no
    planner settings. Fix: every setting is shaped to its type (number and boolean unions, literal unions; a value the
    type does not allow is dropped). The all-components test now feeds settings as strings, like the planner.
12. Rebuilt the saved plan: type check passed (9 s), production build passed (42 s). Checked the pages as text:
    plan texts in place, booking works, no console errors. **Two polish problems:** list samples read like broken
    data ("Sample name 1", "Sample price 1"), and inner pages showed the component's own demo breadcrumbs. Fixes: a
    field-name sample table with a noun from the list ("Service 1", "Rs. 0,000", a real icon name), still obvious
    placeholders (D-225); breadcrumbs made from the page (Home › page).
13. Before the studio run: the backend's auto-reload watched all of `FORGE-1/`, including `builds/`, where preview
    and gate folders link to `node_modules`; a `.py` file there could restart the server in the middle of a build.
    Fix: reload watches only `agents/` and `backend/`. Turned on `FORGE_PREVIEW` and `FORGE_BUILD_GATE` in `.env`.
14. First full run in the studio (Demo Restaurant, an Italian restaurant): clarification asked 2 questions, the brief
    and plan were confirmed, and after approval the frontend agent wrote 11 files, started the preview, wrote the
    pages, and passed the type check (4 s) and production build (20 s). The studio showed the progress, the input
    panel and the live site in the frame. Small fix: "1 sections" → "1 section".
15. **New problem:** reloading the page after the run showed no preview. Cause: my edit to `agent.py` made the
    backend reload, which stops the preview (it lives in memory) and clears the build events. A reload or coming back
    days later would always lose it. Fix: `POST .../preview` starts the preview again from the site's files saved in
    the file store, and the studio calls it when a built request has no preview. Written and type-checked; the
    end-to-end check was interrupted.
16. Seen in the restaurant plan, not a frontend problem: the home page got only a hero section (planning quality).
17. **Reported by Umar:** reopening a built project (Hair Saloon) showed "Step 5 · Plan approved" and no site. The
    backend log showed the studio never asked for the preview. Cause: a built request's status is `planned`
    (`_envelope` in `backend/routes/requests.py`), but the reopen code checked for `complete` (only for runs from
    before planning existed). Fix: check `planned`. Also changed the outdated footer text "Building your site is the
    next step".
18. Retest on another built project (the law firm): the old build log came back, and so did a preview frame, but
    pointing at a dead address (port 55350). One preview runs at a time and later builds had stopped it. Fix: never
    trust an address from the old log. First version: dropped old addresses and then asked the backend.
19. The log replay itself then stalled (the events stream stayed open, sending nothing), and the log is lost on any
    restart anyway. Simpler fix: on reopen, skip the log and ask the backend for the live preview straight away; it
    returns the running preview or starts one from the saved files.
20. **New problem while testing:** opening a project took 40–60 s or more. Timing the database showed it is the
    network, not the code: one of the Supabase pooler's three IPv4 addresses (`13.238.183.126`) times out every time
    from this network, and the other two take 1.3–4.5 s to connect (0.3 s earlier in the day). Every database step
    waits on that. Not an IPv4 problem: all three addresses are IPv4.

21. Retry: the reopen fix worked (the studio asked for the preview at once), but the preview route crashed with a
    raw 500. Two causes in the log: a pooled connection the network had killed ("server closed the connection
    unexpectedly"), and a 30 s pool timeout during a full internet drop. Fixes: the file store's pool tests each
    connection before use (`check_connection`), and the route answers 503 "could not reach its database" instead.
22. **Real root cause of the slowness:** with the network healthy again, every page failed with `EMAXCONNSESSION:
    max clients reached in session mode - limited to pool_size: 15`. Supabase's session pooler allows 15 clients per
    project. FORGE's three pools could open 23 (app engine 5 + 10 overflow, checkpointer 5, file store 3). Fix: caps
    of 6, 4 and 2 (12 in all), and the checkpointer also tests connections before use.
23. Still full after a clean restart: only 5 connections came from this computer. `pg_stat_activity` showed 15
    pooler sessions held, 14 idle since 16:18 UTC: leftovers from backend processes that reloaded or lost the network
    today, which the pooler keeps until its own timeout.

24. With Umar's OK, ended the 15 stuck pooler sessions (`pg_terminate_backend` on idle Supavisor sessions) and
    restarted the backend under the new caps. Reopening the built law-firm project then showed "Opening the live
    preview" → "Live preview is running", and the site (green firm-and-calm look, Home / About Us / Contact / FAQ)
    loaded in the studio from its saved files.

**Status** Fixed and checked end to end: reopening a built project brings its live site back. Lessons: test the
status values a feature depends on against the real envelope; and with a pooler limit of 15, keep FORGE's pools
small and test pooled connections, because restarts and network drops leave sessions behind.

**Status** Working in the studio end to end (request → questions → brief → plan → frontend agent → live site).
Open: the preview-restart path (step 15) is not yet checked end to end; stock photos need an Unsplash key.

## 30. An SEO description over 160 characters ends a valid run
**Symptom** Run 9, content-01: check 7 failed on `home.seo.description` (over 160 characters), one run of two.

**Steps**
1. Same class as issue 28 (search title over 60): the rewrite round asks the model to shorten it, and sometimes it
   does not.

**Status** Open. Likely fix for both: code trims search texts at a word boundary after the rewrite.

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
