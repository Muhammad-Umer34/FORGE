# FORGE-1 Frontend

Next.js 16 (App Router, Cache Components) + React 19 + Tailwind v4. The browser talks only to this site;
`next.config.ts` forwards every `/api/*` call to the FastAPI backend (D-181).

## Pages

| Path | What it shows |
|---|---|
| `/` | Sends signed-in users to `/projects`, others to `/login` |
| `/login`, `/register` | Sign in / create an account (`?next=` returns to the page you came from) |
| `/verify-email?token=` | Opened from the verification email; confirms the address |
| `/forgot-password`, `/reset-password?token=` | Ask for a reset link; choose a new password |
| `/projects` | Your projects (at most 3), create and delete (type the name to confirm) |
| `/projects/[projectId]` | The studio for one project: Describe → Answer → Confirm → Brief, plus earlier requests |

## Structure

- `src/app/`: one folder per page (the App Router needs it).
- `src/components/auth/`: `AuthProvider` (who is signed in), `RequireAuth` (page guard), `AuthForm`, `AuthShell`,
  `EmailVerification` (link page and the "verify your email" banner), `PasswordReset`.
- `src/components/projects/`: projects list, delete dialog, the project page wrapper.
- `src/components/clarification/`: the studio screens and the shared header.
- `src/services/`: `client.ts` (every backend call, token handling), `auth.ts`, `projects.ts`, `requests.ts`.
- `src/types/`: API types mirroring the backend models.
- `src/proxy.ts`: does nothing itself, but makes Next.js pass the visitor's real address to the backend's rate limits (D-195).

## Sign-in in the browser (D-181)

- The **access token** (15 min) is kept in memory only, never in `localStorage`.
- The **refresh token** is an HttpOnly cookie that only `/api/auth/*` receives, so scripts can't read it.
- On page load the app renews the session from that cookie. A call that answers 401 renews once and retries;
  tabs take turns renewing (Web Locks), and a 409 from the backend means "another tab just did it, retry".
- The page guard only redirects; the backend checks the token on every projects and requests call.
- If FORGE has reached its daily email limit, sign-up still works and the verify-email banner shows the backend's
  `notice` instead of "We sent a link" (D-194). Limit answers (429, 413) show the backend's message.

## Run

```bash
npm run dev
```

The backend must run on `http://localhost:8000` (or set `BACKEND_URL` for the dev server). Open http://localhost:3000.
