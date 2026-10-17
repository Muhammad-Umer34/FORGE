# FORGE-1 Backend

FastAPI server for FORGE. It runs the agent pipeline (`agents/`) behind a small HTTP API.
Model calls go through the LLM gateway in `agents/gateway.py` (Google Gemini; model ids from `.env`).

**Model provider (D-184).** Calls go to **Vertex AI** (Google Cloud project `gen-lang-client-0455463515`, so they use the
project's credits) whenever `VERTEX_API_KEY` is set; otherwise to the Google AI Studio API with `STUDIO_API_KEY`.
`LLM_PROVIDER=vertex|studio` forces one. Primary and fallback model always use the same provider. Two traps, handled:
- The Google SDK reads `GEMINI_API_KEY` / `GOOGLE_API_KEY` by itself and prefers them in Vertex mode, so the AI Studio key
  is stored as `STUDIO_API_KEY`; the gateway refuses to start a call if either old name is set.
- `GOOGLE_CLOUD_PROJECT` / `GOOGLE_CLOUD_LOCATION` would switch the SDK to service-account login, so `.env` uses
  `VERTEX_PROJECT` / `VERTEX_LOCATION` (for reference only; the key already names the project).
Gemini 3 models are served from the `global` location only (`us-central1` answers 404 for them).

## Architecture

- `core/`: settings and environment configuration (`config.py`); shared dependencies (`deps.py`, incl. the signed-in user); passwords and tokens (`security.py`).
- `db/`: PostgreSQL (Supabase) connection (`session.py`) and table definitions (`tables.py`) (D-172).
- `migrations/`: Alembic migrations; `versions/0001_users_and_projects.py` creates users, projects and the 3-project limit (D-173, D-175); `0002_refresh_tokens.py` adds sign-in sessions (D-178); `0003_requests.py` links website requests to projects (D-179).
- `models/`: Pydantic request and response schemas (`requests.py` for the website-request API; `auth.py`; `projects.py`).
- `routes/`: `requests.py` (website-request API), `auth.py` (sign-in), `projects.py`, `health.py`.
- `services/`: `auth.py` (accounts and sign-in sessions, D-176 – D-178); `projects.py` (the only code that creates or deletes projects, D-174); `requests.py` (which requests belong to whom, D-179, D-180).
- `main.py`: application bootstrap, CORS, and the checkpointer that keeps paused runs.

The old free chat (`/api/chat`) was removed once the sign-in, projects and studio screens replaced it (D-137, D-182).

Configuration is read from the single `.env` file at the FORGE-1 root. Agents never write to the database (D-133); only the API layer does.

## Database (PostgreSQL on Supabase)

`.env` keys: `SUPABASE_DB_URL` (app), `TEST_DATABASE_URL` (integration tests), `DB_LOCK_TIMEOUT_MS` (default 3000).

```powershell
.venv\Scripts\python.exe -m alembic -c backend/migrations/alembic.ini upgrade head            # app database
.venv\Scripts\python.exe -m alembic -c backend/migrations/alembic.ini -x db=test upgrade head  # test database
```

## Sign-in API (D-176 – D-178)

| Method and path | Body | Answer |
|---|---|---|
| `POST /api/auth/register` | `{ "email", "password" (8–128), "display_name" }` | 201 + access token; 409 `email_taken` |
| `POST /api/auth/login` | `{ "email", "password" }` | 200 + access token; 401 `invalid_credentials`; 429 `account_locked` after 5 wrong passwords (15 min) |
| `POST /api/auth/refresh` | — (cookie) | 200 + new access token and new cookie; 401 `signed_out`; 409 `refresh_in_progress` (another tab renewed a moment ago: retry, cookie kept) |
| `POST /api/auth/logout` | — (cookie) | 204, ends this sign-in on every device it reached |
| `GET /api/auth/me` | — (`Authorization: Bearer <access token>`) | the signed-in user |

- **Access token:** JWT (HS256), 15 minutes, sent as `Authorization: Bearer …`. The frontend keeps it in memory only.
- **Refresh token:** JWT with its own secret, 14 days, only in the `forge_refresh` cookie (HttpOnly, SameSite=Lax,
  Path=/api/auth, Secure outside development). Stored as a SHA-256 hash. Every refresh replaces it; an old one used
  again later revokes the whole sign-in (theft detection). Used again within 10 seconds (two tabs) it is just refused.
- **Passwords:** Argon2id. `.env` needs `JWT_ACCESS_SECRET` and `JWT_REFRESH_SECRET` (different, at least 32 characters).

**Project limit (D-174, D-175):** at most 3 projects per user. `services/projects.create_project` locks the user's row
(`SELECT ... FOR UPDATE`), counts, then inserts, all in one READ COMMITTED transaction; a trigger in the database does the
same as a safety net. Any new code that creates projects must call `create_project`.

## Website-request API (Clarification Agent)

Every request belongs to a project of the signed-in user, so every path starts with `/api/projects/{pid}/requests`
and needs `Authorization: Bearer <access token>` (D-179). A request in someone else's project, or in another project
of the same user, answers 404 before the agent is touched.

Every response has the same envelope: `{ "request_id", "status", "data" }`.
`status` is one of `needs_clarification`, `awaiting_confirmation`, `complete`, `out_of_scope`, `failed`, `cancelled`, `reply`.

| Method and path (prefix `/api/projects/{pid}/requests`) | Body | Notes |
|---|---|---|
| `GET` | — | The project's requests, newest first: id, prompt, status, times |
| `POST` | `{ "prompt": "..." }` | Starts a run; a greeting (`reply`) is answered but not kept |
| `GET /{id}` | — | Current envelope (for page reloads) |
| `POST /{id}/answer` | `{ "question_id", "kind": "option \| you_decide \| other", "option_ids": [], "text": null }` | 422 if the answer does not fit the question |
| `POST /{id}/confirmation` | `{ "decision": "confirm \| edit \| cancel \| theme_source", ... }` | 422 if the action is not available |
| `POST /{id}/image?kind=logo\|screenshot` | multipart file | Colours from a logo or screenshot |

The `requests` table keeps each request's project, prompt and latest status. Paused runs are stored in
`forge_checkpoints.db` at the FORGE-1 root (gitignored), so they survive a restart. Deleting a project deletes its
requests and their paused runs (D-180).

## Projects API (D-174)

`GET /api/projects`, `POST /api/projects` `{ "name", "description" }` (409 `project_limit_reached` at 3),
`DELETE /api/projects/{pid}` (for good, with everything in it). All need the access token.

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
PostgreSQL integration tests (`tests/test_project_limit.py`, `tests/test_auth.py`; helpers in `tests/pg_support.py`) run only
when `TEST_DATABASE_URL` is set; they apply the migrations, create their own users and delete them afterwards (about 8
minutes against the Supabase pooler).
