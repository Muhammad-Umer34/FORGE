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
- `migrations/`: Alembic migrations; `versions/0001_users_and_projects.py` creates users, projects and the 3-project limit (D-173, D-175); `0002_refresh_tokens.py` adds sign-in sessions (D-178); `0003_requests.py` links website requests to projects (D-179); `0004_email_tokens.py` adds email verification and password reset (D-185, D-186).
- `models/`: Pydantic request and response schemas (`requests.py` for the website-request API; `auth.py`; `projects.py`).
- `routes/`: `requests.py` (website-request API), `auth.py` (sign-in), `projects.py`, `health.py`.
- `services/`: `auth.py` (accounts and sign-in sessions, D-176 – D-178); `projects.py` (the only code that creates or deletes projects, D-174); `requests.py` (which requests belong to whom, D-179, D-180); `email_flows.py` (verification and reset links, D-185, D-186); `mailer.py` (sends email over SMTP, D-187).
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
| `POST /api/auth/login` | `{ "email", "password" }` | 200 + access token; 401 `invalid_credentials`; 429 `account_locked` after 5 wrong passwords from one address (15 min, D-192) |
| `POST /api/auth/refresh` | — (cookie) | 200 + new access token and new cookie; 401 `signed_out`; 409 `refresh_in_progress` (another tab renewed a moment ago: retry, cookie kept) |
| `POST /api/auth/logout` | — (cookie) | 204, ends this sign-in on every device it reached |
| `GET /api/auth/me` | — (`Authorization: Bearer <access token>`) | the signed-in user |

- **Access token:** JWT (HS256), 15 minutes, sent as `Authorization: Bearer …`. The frontend keeps it in memory only.
- **Refresh token:** JWT with its own secret, 14 days, only in the `forge_refresh` cookie (HttpOnly, SameSite=Lax,
  Path=/api/auth, Secure outside development). Stored as a SHA-256 hash. Every refresh replaces it; an old one used
  again later revokes the whole sign-in (theft detection). Used again within 10 seconds (two tabs) it is just refused.
- **Passwords:** Argon2id. `.env` needs `JWT_ACCESS_SECRET` and `JWT_REFRESH_SECRET` (different, at least 32 characters).

### Email verification and password reset (D-185 – D-188)

| Method and path | Body | Answer |
|---|---|---|
| `POST /api/auth/verify-email` | `{ "token" }` | the user, now verified; 400 `invalid_link` |
| `POST /api/auth/resend-verification` | — (access token) | 202; 409 `already_verified`; 429 `too_many_emails` |
| `POST /api/auth/forgot-password` | `{ "email" }` | always 202 with the same message |
| `POST /api/auth/reset-password` | `{ "token", "password" }` | 200; 400 `invalid_link` |

- Registering sends a verification link (24 h). A reset link lasts 30 min. Links work once, are stored only as SHA-256
  hashes, and a new link cancels the older ones. At most 3 links of each kind per account per hour.
- **Unverified users can sign in but cannot create projects or run requests** (403 `email_not_verified`). The access
  token carries `ev` (email verified); after verifying, the frontend refreshes the session to get a new token.
- A reset changes the password, clears any lockout, marks the email verified and signs the account out everywhere.
- Mail is sent after the answer (FastAPI background task) over SMTP. `.env`: `SMTP_HOST`, `SMTP_PORT` (587 STARTTLS or
  465 TLS), `SMTP_USERNAME`, `SMTP_PASSWORD`, `MAIL_FROM`, `FRONTEND_URL` (where the links point). Without `SMTP_HOST` the
  email, with its link, is only written to the log. Tests capture emails and never send them.

**Project limit (D-174, D-175):** at most 3 projects per user. `services/projects.create_project` locks the user's row
(`SELECT ... FOR UPDATE`), counts, then inserts, all in one READ COMMITTED transaction; a trigger in the database does the
same as a safety net. Any new code that creates projects must call `create_project`.

## Cost and abuse limits (D-189 – D-194)

Counted in the `rate_limits` table (migration 0005), so they hold across restarts. Every number is a setting in
`backend/core/config.py` that `.env` can change. A limit reached answers 429 with a `Retry-After` header.

| What | Limit | Setting |
|---|---|---|
| New website requests | 20 per user per day, 300 for the app per day | `LIMIT_REQUESTS_PER_USER_DAY`, `LIMIT_REQUESTS_PER_DAY` |
| Steps of one request | one at a time; a second answer or confirmation meanwhile gets 409 | — |
| Sign-ups | 5 per hour and 20 per day per address, 200 for the app per day | `LIMIT_SIGNUPS_PER_IP_*`, `LIMIT_SIGNUPS_PER_DAY` |
| "Forgot password" | 10 per hour per address | `LIMIT_FORGOT_PER_IP_HOUR` |
| Emails | 400 per day for the app (Gmail allows ~500); sign-up still works and says the link was not sent | `LIMIT_EMAILS_PER_DAY` |
| Wrong passwords | 5 from one address lock that address for that account (15 min); 30 per account per hour from anywhere lock the account; 30 per address in 10 min block the address | `LIMIT_LOGIN_FAILS_*` |
| Website reads / image reads | 10 per user per day / 30 per user per hour | `LIMIT_WEBSITE_READS_PER_USER_DAY`, `LIMIT_IMAGE_READS_PER_USER_HOUR` |
| Reader browsers | 2 at once; a request waits up to 20 s, then hears FORGE is busy | env `READER_MAX_BROWSERS`, `READER_WAIT_S` |
| Body size | 64 KB; image uploads 2.5 MB (413 before the body is read) | `MAX_JSON_BODY_BYTES`, `MAX_IMAGE_UPLOAD_BYTES` |

The client address is the connection's, or the first `X-Forwarded-For` entry only when the connection comes from this
machine (the Next.js proxy). `frontend/src/proxy.ts` makes Next.js fill that header with the visitor's real address
(without it every visitor arrived as 127.0.0.1). Next.js keeps a header the visitor sent themselves, so in production
put Caddy or nginx in front and have it replace `X-Forwarded-For` with the real address (D-195).

A new request whose agent run fails (e.g. the model is down) is saved as `failed` and is not counted against the
daily limits (D-196).

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

| `POST /{id}/resume` | — | Continues a **paused** request from its last saved step; 409 if it is not paused or already running, 429 after 5 resumes in an hour |
| `POST /{id}/cancel` | — | Ends the current request (paused, waiting for an answer, or with a finished brief) and deletes its saved run; used by *Start over* |

The `requests` table keeps each request's project, prompt and latest status. Deleting a project deletes its
requests and their saved runs (D-180).

**One project = one website (D-200).** `POST` (new request) answers 409 `website_in_progress` while the
project's latest request is processing, waiting for an answer, paused, or has a finished brief. *Start over*
cancels it first; a different website belongs in a new project.

### Persistence and resume (D-197 – D-199)

- **Every step is saved** in PostgreSQL (LangGraph `AsyncPostgresSaver`, tables `checkpoint*` created at start-up)
  before the next one starts, including the steps inside each agent's subgraph.
- **Run states**, read from the saved run: *waiting for user* (question or confirmation), *working*, *paused*
  (stopped mid-way by a crash or a model outage), *finished*, or *missing* (nothing saved). `GET /{id}` returns
  `paused` or `processing` when that applies and corrects the stored status.
- **Continue:** `POST /{id}/resume` runs again only the step that was cut off; finished steps are never repeated.
- **Start-up:** requests left on `processing` by a crash are set to their real state (usually `paused`).
- **Windows:** psycopg needs a SelectorEventLoop; `python -m backend.main` starts uvicorn with one. Running
  `uvicorn` by hand on Windows needs `--loop asyncio:SelectorEventLoop`.
- **Rules for agents:** one model call per step, waiting steps contain only `interrupt()`, and raise
  `STATE_VERSION` in `agents/state.py` when old runs can no longer be continued.

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

- Server URL: `http://localhost:8000` (listens on this machine only; set `HOST=0.0.0.0` in `.env` to open it to the network)
- API Documentation (Swagger UI): `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

## Tests

```powershell
cd d:\FYP\FORGE-1
.venv\Scripts\python.exe -m pytest tests -q
```

Live tests call Gemini and use API credits; they run only with `FORGE_LIVE_TESTS=1`.
PostgreSQL integration tests (`tests/test_project_limit.py`, `tests/test_auth.py`, `tests/test_limits.py` and others; helpers in `tests/pg_support.py`) run only
when `TEST_DATABASE_URL` is set; they apply the migrations, create their own users and delete them afterwards (about 8
minutes against the Supabase pooler). `tests/conftest.py` raises every rate limit for each test; the limit tests
lower the one they check and use made-up addresses so counters never collide.
