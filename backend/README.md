# FORGE-1 Backend

FastAPI server for FORGE. It runs the agent pipeline (`agents/`) behind a small HTTP API.
Model calls go through the LLM gateway in `agents/gateway.py` (Google Gemini; model ids from `.env`).

## Architecture

- `core/`: settings and environment configuration (`config.py`); shared dependencies (`deps.py`); the old chat prompt (`prompts.py`).
- `db/`: PostgreSQL (Supabase) connection (`session.py`) and table definitions (`tables.py`) (D-172).
- `migrations/`: Alembic migrations; `versions/0001_users_and_projects.py` creates users, projects and the 3-project limit (D-173, D-175).
- `models/`: Pydantic request and response schemas (`requests.py` for the website-request API; `projects.py`; `chat.py`, `session.py` for the old chat).
- `routes/`: `requests.py` (website-request API), `projects.py` (not registered until sign-in exists), `health.py`, and the old `chat.py`.
- `services/`: `projects.py` (the only code that creates or deletes projects, D-174); the old chat's Gemini and memory services.
- `main.py`: application bootstrap, CORS, and the checkpointer that keeps paused runs.

The old free chat (`/api/chat`, `services/`, `models/chat.py`, `models/session.py`, `core/prompts.py`) stays until the
new clarification screen exists, then it is deleted in one cleanup step (decision D-137).

Configuration is read from the single `.env` file at the FORGE-1 root. Agents never write to the database (D-133); only the API layer does.

## Database (PostgreSQL on Supabase)

`.env` keys: `SUPABASE_DB_URL` (app), `TEST_DATABASE_URL` (integration tests), `DB_LOCK_TIMEOUT_MS` (default 3000).

```powershell
.venv\Scripts\python.exe -m alembic -c backend/migrations/alembic.ini upgrade head            # app database
.venv\Scripts\python.exe -m alembic -c backend/migrations/alembic.ini -x db=test upgrade head  # test database
```

**Project limit (D-174, D-175):** at most 3 projects per user. `services/projects.create_project` locks the user's row
(`SELECT ... FOR UPDATE`), counts, then inserts, all in one READ COMMITTED transaction; a trigger in the database does the
same as a safety net. Any new code that creates projects must call `create_project`.

## Website-request API (Clarification Agent)

Every response has the same envelope: `{ "request_id", "status", "data" }`.
`status` is one of `needs_clarification`, `awaiting_confirmation`, `complete`, `out_of_scope`, `failed`, `cancelled`.

| Method and path | Body | Notes |
|---|---|---|
| `POST /api/requests` | `{ "prompt": "...", "project_id": null }` | Starts a run |
| `POST /api/requests/{id}/answer` | `{ "question_id", "kind": "option \| you_decide \| other", "option_ids": [], "text": null }` | 422 if the answer does not fit the question |
| `POST /api/requests/{id}/confirmation` | `{ "decision": "confirm \| edit \| cancel", "ticked_extra_ids": [], "unticked_default_ids": [], "style": null, "edit_text": null }` | 422 if the action is not available |
| `GET /api/requests/{id}` | — | Current envelope (for page reloads) |

Paused runs are stored in `forge_checkpoints.db` at the FORGE-1 root (gitignored), so they survive a restart.

## Setup (once)

From the FORGE-1 root:

```powershell
cd d:\FYP\FORGE-1
py -3.13 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## How to Start the Backend

Always run from the FORGE-1 root, so both `backend` and `agents` are importable:

```powershell
cd d:\FYP\FORGE-1
.venv\Scripts\python.exe -m backend.main
```

- Server URL: `http://localhost:8000`
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Tests

```powershell
cd d:\FYP\FORGE-1
.venv\Scripts\python.exe -m pytest tests -q
```

Live tests call Gemini and use API credits; they run only with `FORGE_LIVE_TESTS=1`.
PostgreSQL integration tests (`tests/test_project_limit.py`) run only when `TEST_DATABASE_URL` is set; they apply the
migrations, create their own users and delete them afterwards (about 4 minutes against the Supabase pooler).
