# FORGE documentation

FORGE is the team's FYP (Muhammad Sachal, Muhammad Qudama, Muhammad Umar; supervisor Dr. Zareen Alamgir):
an AI multi-agent website builder. This folder records **what was built, what was decided and why**,
kept up to date with every change.

| Document | What it holds | Updated |
|---|---|---|
| [decision-log.md](decision-log.md) | Every decision, one row each: what, why (with evidence), alternatives rejected, status, owner. D-001 onwards. | With every decision |
| [worklog.md](worklog.md) | What was done, when and why, newest first: commits, decisions, checks, open items | After every piece of work |
| [known-issues.md](known-issues.md) | Open bugs and scope limits, and what was fixed by which commit | When an issue is found or fixed |
| [progress.md](progress.md) | The scoreboard of every evaluation run (what changed the numbers) and every issue met: how it was found, its cause and its fix | After every evaluation run and every issue found |

Design documents, reports and research live outside the codebase (D-008):
- `D:/FYP/FORGE-DOCUMENTS/` — designs (`FORGE_Clarification_Agent_Plan_v6.md`), proposal, plans, notes.
- `D:/FYP/reports/` — research reports and plans (e.g. *Planning Agent plan v2*, *FORGE persistence plan*,
  *FORGE agent scope review*).
- `D:/FYP/research_notes/` — the notes behind each report.

Code-level documentation: `agents/README.md` (the run and each agent's modules), `backend/README.md`
(API, database, models), `components/README.md` (catalogue and Component Needs List).

## Rules

1. **Every decision is logged** in `decision-log.md` before or with the change that implements it:
   ID, date, what, why (with evidence such as a failed run or a source), alternatives rejected, status, owner.
2. **Decisions are never deleted.** A changed decision gets a new ID and the old one is marked
   *Superseded by D-xxx* (or the new row says which part it supersedes).
3. **Every piece of work gets a work-log entry**: what, why, decisions, commits, how it was checked, and
   what is still open. Newest first.
4. **Issues are tracked** in `known-issues.md`; a fix sets the status to Fixed with its commit and decision.
5. **Commit messages name the decisions** they implement, e.g. `(D-211)`.
6. Documentation changes go in the same commit as the code they describe.
7. **Every evaluation run adds a scoreboard row** to `progress.md` (date, commit, models, numbers, and what caused
   the change), and **every issue met adds a line** to its issues table (how it was found, cause, fix, decision),
   including invalid runs and issues found by tests.

Status values in the decision log: **Implemented** (done and checked), **Approved** (agreed, not built),
**Proposed** (waiting for approval), **Rejected**, **Superseded**.
