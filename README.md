# 🚀 Recruvoskill - AI-Native Hiring Platform

**Recruvoskill** is an AI-native hiring platform that evaluates candidates on real evidence of work — GitHub repositories and competitive-programming activity — instead of resumes. It extracts objective signals (tests, CI/CD, deployment artifacts, web frameworks, Codeforces/LeetCode activity), scores every candidate against every task with a human-readable reason for each score, and lets a recruiter make an Advance/Reject decision per candidate that's the *only* thing the candidate ever sees — never the raw number.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED)

---

## ✨ Features

### For Recruiters
- Define outcome-based job postings and let AI decompose them into verifiable tasks
- Tag an outcome with a job role (Backend, Frontend, Data/ML, DevOps, QA, Mobile, etc.) so candidates can filter by it
- Scoring runs automatically as candidates apply — no manual "run evaluation" step
- Review a per-outcome candidate roster (name, GitHub username, email) and open any candidate to see their task-by-task score and reasons
- Decide **Advance to Interview** or **Reject** per candidate — once decided, that candidate can't be reopened
- Send the candidate feedback alongside the decision — AI-drafted from their actual task scores/reasons, or written by hand, always editable before sending
- Own and manage only the outcomes you created — enforced server-side, not just hidden in the UI

### For Candidates
- Browse public job postings without an account, filterable by job role
- Sign up by proving ownership of a real GitHub account (OAuth + email/username confirmation + OTP) — no plain email/password signup exists for candidates
- Submit a GitHub repo as proof of work; optionally link a Codeforces handle and/or LeetCode username so DSA-focused tasks can score against real problem-solving activity, not just repo signals
- View your own application status only — `Pending` → `Under Review` → `Advancing to Interview` / `Rejected`, plus any feedback the recruiter left. The underlying score is never exposed to a candidate.

### Technical Features
- **Signal Extraction** — detects tests, migrations, CI/CD, deployment config, ML models/libraries, web frameworks, frontend templates from a repo's real file tree via the GitHub REST API
- **Coding-platform signals** — Codeforces (signed API) rating + solved-problem counts, and LeetCode (GraphQL) solved counts, normalized into a single `dsa_proficiency` score
- **Rule-based scoring engine** — task-title keywords map to relevant signals, averaged into a score, with a `Found:` / `Missing:` reason tied to that exact task (`app/pipeline/matcher.py`); this is deterministic, not an LLM call
- **GenAI, used narrowly** — Groq (`openai/gpt-oss-120b`) turns a job description into verifiable tasks, and drafts qualitative candidate feedback from real task scores (no leaked percentages) — the scoring engine itself has zero AI in it
- **GitHub-verified candidate identity** — OAuth + a typed email/username confirmation checked against what GitHub's API actually reports, closing the "shared/already-logged-in laptop" impersonation gap that OAuth alone doesn't cover
- **JWT authentication with roles** — admin / recruiter / candidate, enforced on every protected endpoint
- **SEO-indexable public job pages** — server-rendered per-job pages with JobPosting structured data, `robots.txt`, `sitemap.xml`
- **Audit logging** — admin-visible log of outcome/proof/evaluation/decision actions
- **Dockerized local dev** — one `docker-compose up` runs both services against your MongoDB Atlas cluster

---

## 🔐 Authentication & Roles

Auth is JWT-based. Passwords are hashed with bcrypt; tokens are signed with `JWT_SECRET_KEY` and expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).

| Role | Can do |
|------|--------|
| **candidate** | Browse public jobs, submit proofs, link coding-platform profiles, view *only their own* applications/status (never a score) |
| **recruiter** | Create outcomes, review the candidate roster, decide Advance/Reject with optional feedback — *for outcomes they own* |
| **admin** | Everything a recruiter can do across all outcomes, plus audit logs and signal-weight config |

`POST /auth/register` only ever creates **recruiter** accounts — candidates cannot self-register with a plain email/password at all (see GitHub verification below). `admin` is never reachable through any public endpoint. To create the first admin:

```bash
cd backend
venv/bin/python scripts/promote_admin.py you@example.com   # after registering that account normally as a recruiter
```

Every authorization rule above is enforced in the backend (`app/deps/auth.py`, ownership checks in each route) — the frontend's route guards (`ProtectedRoute`) are a UX convenience only, not a security boundary.

**Candidate identity**: a candidate's identity comes from their JWT, never from a client-supplied id or email. `POST /proofs` overwrites whatever `candidate_id` the client sends with the authenticated user's email server-side, and `GET /candidate/my-applications` takes no id parameter at all.

**Forgot password**: `POST /auth/forgot-password` (email) → `POST /auth/reset-password` (email, 6-digit OTP, new password). The OTP is hashed (sha256), single-use, capped at `PASSWORD_RESET_MAX_ATTEMPTS` wrong guesses, rate-limited to one request per `PASSWORD_RESET_COOLDOWN_SECONDS` per email, and the endpoint always returns the same generic message regardless of whether the email is registered. **Requires SMTP configuration** to actually deliver the email — without it, the code is only logged server-side (dev convenience only).

**GitHub verification (candidates only)** — two entry points, both end the same way:
- **"Continue with GitHub"** (`GET /auth/github/login`) — real GitHub OAuth, then the candidate must type both the email *and* username connected to that GitHub account before any OTP is sent (checked against what GitHub's API actually reports, not anything self-declared) — an OTP to a mismatched account is never sent.
- **Password signup** (`POST /auth/register/candidate/start`) — candidate picks an email/password and *claims* a GitHub username; the account is not created until they complete real GitHub OAuth as that exact account and confirm the same email/username + OTP.

Both flows converge on `POST /auth/github/verify-otp`, which is the only thing that ever creates/links/logs in — nothing happens before it succeeds. `GET /auth/github/connect` (authenticated) lets a recruiter/admin optionally link GitHub to an existing account the same way. One account can link at most one GitHub account and vice versa (partial unique index on `users.github_id`). **Requires a registered GitHub OAuth App** (`GITHUB_OAUTH_CLIENT_ID`/`GITHUB_OAUTH_CLIENT_SECRET`, callback URL `{PUBLIC_BASE_URL}/auth/github/callback`) — without it, the GitHub routes return `503`, not a crash.

---

## 🧮 Coding-Platform Signals (Codeforces / LeetCode)

Candidates optionally link a Codeforces handle and/or LeetCode username via `GET`/`PATCH /candidate/coding-profiles` (and `POST .../refresh` to re-pull stats later). Self-reported — neither platform has an OAuth flow to verify ownership the way GitHub does.

- **Codeforces** (`app/services/codeforces.py`) — signed requests per their real public API (`codeforces.com/apiHelp`); works unsigned too, just at a lower rate limit. A handle that doesn't exist is rejected immediately (real error, not silently stored).
- **LeetCode** (`app/services/leetcode.py`) — the same unauthenticated GraphQL endpoint leetcode.com's own frontend uses; no official API exists, so a failed fetch is stored as "unavailable" rather than blocking the request.
- **Normalization** (`app/services/dsa_signals.py`) — Codeforces takes the *higher* of a rating-based score (2100 = full) and a solved-count score (300 = full); LeetCode is solved-count only; the two platforms combine by taking whichever is stronger, not an average, so using only one platform never penalizes a candidate.

This feeds into task matching as `dsa_proficiency`, alongside the GitHub signals — a task titled e.g. "Strong algorithms and data structures" scores from this instead of repo signals. Cached at link/refresh time, not fetched live during evaluation, so a Codeforces/LeetCode outage can never break a batch evaluation run.

---

## 🎯 Job Roles

Outcomes can be tagged with a job role from a fixed list (`app.constants.JobRole` — Backend, Frontend, Full Stack, Mobile, Data/ML, DevOps, QA, General SDE). `GET /job-roles` is the single source of truth both the recruiter's outcome form and the candidate's job-filter dropdown read from. `GET /outcomes` and `GET /candidate/jobs` both accept `?job_role=` to filter.

---

## 👥 Recruiter Workflow: Roster & Decisions

There is no "run evaluation" button. `GET /outcomes/{id}/candidates` (the dashboard's roster) triggers scoring transparently for any unscored applicant, then lists every candidate with their name/GitHub username/email. Clicking a candidate opens their real task-by-task scores and two actions:

- `POST /evaluations/{job_id}/decision` — records `advancing` or `rejected`, plus optional feedback text, for one candidate. This is the **only** thing `GET /candidate/my-applications` ever reflects — the raw score never reaches a candidate.
- `POST /evaluations/{job_id}/feedback/suggest` — drafts feedback from that candidate's real task scores/reasons via the LLM (never mentions raw percentages); the recruiter can edit it or ignore it and write their own before sending.

Once a candidate is decided, the recruiter can't reopen their score page. Decisions and feedback survive a later re-evaluation (e.g. a new candidate applying) — a fresh evaluation run carries forward everything already decided rather than silently resetting it.

---

## 🌐 Public SEO Job Pages

Because the frontend is a client-rendered Vite SPA, its routes aren't crawlable — a search engine would see an empty `<div id="root">`. Rather than migrating the whole app to a new framework, the backend serves a small set of server-rendered public pages directly (Jinja2, `app/templates/job.html`):

- `GET /jobs/{outcome_id}` → 301 to the canonical slug URL
- `GET /jobs/{outcome_id}/{slug}` → full HTML page: title, description, tasks, `<link rel="canonical">`, Open Graph tags, and `schema.org/JobPosting` JSON-LD
- `GET /robots.txt`, `GET /sitemap.xml` → only outcomes with `is_public=true`

In production, `frontend/vercel.json` proxies `/jobs/*`, `/robots.txt`, and `/sitemap.xml` from the frontend's domain to this backend, so crawlers see one consistent public domain. **You must replace `YOUR-BACKEND-DOMAIN.onrender.com` in `frontend/vercel.json` with your actual deployed backend URL** — this can't be known until you've deployed once.

**Limitation**: the JobPosting schema always sets `jobLocationType: TELECOMMUTE` / `employmentType: CONTRACTOR` as a reasonable default, since outcomes don't currently model location or employment type.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   React Frontend │────▶│  FastAPI Backend │────▶│  MongoDB Atlas   │
│   (Vite + JSX)   │     │   (Python 3.12)  │     │  (PyMongo async) │
└─────────────────┘     └────────┬─────────┘     └──────────────────┘
                                 │
              ┌──────────┬───────┼───────┬──────────────┐
              ▼          ▼       ▼       ▼              ▼
         ┌─────────┐ ┌──────┐ ┌─────┐ ┌────────────┐ ┌────────────┐
         │ GitHub  │ │ Groq │ │Signal│ │ Codeforces │ │  LeetCode  │
         │   API   │ │ LLM  │ │Engine│ │    API     │ │  GraphQL   │
         └─────────┘ └──────┘ └─────┘ └────────────┘ └────────────┘
```

The backend talks to MongoDB via PyMongo's native async API (`pymongo.AsyncMongoClient` — no Motor). One client is created at FastAPI startup (`lifespan`) and reused for every request; it's closed cleanly on shutdown. `_ensure_indexes()` runs on every startup, so a brand-new database gets its full collection/index structure automatically — no manual migration step.

---

## 🚀 Local Setup

### Option A — Docker (recommended)

```bash
docker compose up --build -d
```

Runs both services in containers: backend on `:8001` (`uvicorn --reload`), frontend on `:5175` (Vite dev server). Both bind-mount your source, so edits reload live. The backend reads `backend/.env` directly and connects to your MongoDB Atlas cluster (no local Mongo container needed). Requires `backend/.env` to already exist (see below) before the first `up`.

```bash
docker compose logs -f     # tail logs
docker compose down        # stop
```

If you change `requirements.txt` or `package.json`, rebuild with `docker compose up -d --force-recreate`, not just `restart` — `restart` reuses the container's already-baked environment and won't pick up dependency or `.env` changes.

### Option B — Manual

**Prerequisites**: Python 3.10+, Node.js 18+, a MongoDB Atlas account (or local `mongod`), a GitHub token + OAuth App, and a Groq API key (the app runs without them but falls back to reduced/mock behavior).

#### MongoDB Atlas setup
1. Create a free cluster at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas).
2. **Database Access** → add a database user.
3. **Network Access** → add your current IP (or `0.0.0.0/0` for unrestricted dev access — never in production).
4. **Database → Connect → Drivers** → copy the `mongodb+srv://...` connection string.

#### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env: at minimum set MONGODB_URI, GROQ_API_KEY, GITHUB_TOKEN, JWT_SECRET_KEY
# (generate a JWT secret with: python -c "import secrets; print(secrets.token_hex(32))")

uvicorn app.main:app --reload --port 8001
```

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Access
- Frontend: http://localhost:5175
- Backend API + docs: http://localhost:8001 / http://localhost:8001/docs

---

## 🧪 Tests

```bash
cd backend
venv/bin/python -m pytest -q
```

176+ tests, run against `MONGODB_TEST_DATABASE`, never your real `MONGODB_DATABASE` — `tests/conftest.py` forces `ENVIRONMENT=test`, and `config.MONGODB_ACTIVE_DATABASE` always resolves to the test database whenever that's set. Collections are truncated before every test. Needs a reachable MongoDB at `MONGODB_URI` — tests don't spin up their own server. External services (Groq, GitHub OAuth) are force-blanked/mocked in `conftest.py` so a real developer `.env` can never leak into a test run; Codeforces/LeetCode calls are mocked per-test at the HTTP boundary. Coverage includes: registration/login/JWT validation, GitHub OAuth (email+username confirmation, OTP), role-based authorization, cross-user/cross-recruiter access denial (IDOR), outcome/proof/evaluation flows, coding-platform signal scoring, job-role filtering, the candidate-decision/feedback workflow (including the re-evaluation-preserves-decisions regression), CORS, invalid ObjectId handling, duplicate-key handling, and production error-response shape.

Frontend build check:
```bash
cd frontend
npm run build
```

---

## 🔑 Environment Variables

See `backend/.env.example` for the full list with descriptions. Summary:

```env
ENVIRONMENT=development        # development | production | test
DEMO_MODE=false                # true = silently mock AI/GitHub failures (dev/demo only)
MONGODB_URI=mongodb+srv://username:password@cluster.mongodb.net/
MONGODB_DATABASE=signaxai
MONGODB_TEST_DATABASE=signaxai_test
JWT_SECRET_KEY=                # required in production, no default
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175
GITHUB_TOKEN=                  # personal access token, for repo signal analysis
GROQ_API_KEY=
PUBLIC_BASE_URL=http://localhost:8001
FRONTEND_BASE_URL=http://localhost:5175

# GitHub OAuth App — candidate identity verification ("Continue with GitHub")
GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
GITHUB_OAUTH_REDIRECT_URI=http://localhost:8001/auth/github/callback

# SMTP — forgot-password and GitHub-verification OTP emails
SMTP_HOST=
SMTP_USER=
SMTP_PASSWORD=

# Codeforces — optional, public data works unsigned too; see codeforces.com/settings/api
CODEFORCES_API_KEY=
CODEFORCES_API_SECRET=
```

`GITHUB_TOKEN`, `GROQ_API_KEY`, `MONGODB_URI`, SMTP/OAuth secrets, and Codeforces keys are backend-only and are never exposed to the browser — the frontend only ever receives `VITE_API_BASE_URL`. Never put a real `MONGODB_URI` (it contains credentials) into source code, this README, `.env.example`, or a Vite `VITE_*` variable.

---

## 🛡️ Security Notes

- **CORS** is an explicit allowlist (`CORS_ORIGINS`), never `*` — required, since the API uses credentialed requests.
- **Errors**: in production (`ENVIRONMENT=production`), unhandled exceptions return `{"detail": "Internal server error", "request_id": "..."}` — no stack traces, file paths, or internal messages reach the client. Full detail is logged server-side against the same `request_id`.
- **GitHub URL handling**: only `github.com` hosts are accepted; the backend never fetches an arbitrary URL a client supplies (guards against SSRF via the repo-analysis feature). Same host restriction applies to the Codeforces client (only `codeforces.com`).
- **Upstream failures** (GitHub/Groq/Codeforces) return categorized, machine-readable errors instead of raw exception text or a silently faked result — unless `DEMO_MODE=true`.
- **Database errors**: PyMongo exceptions are never returned to clients — `app/services/mongo_errors.py` maps them to clean responses (e.g. a duplicate-key error becomes `409`). The raw exception is always logged server-side only.
- **ObjectId handling**: Mongo `_id` values are converted to plain strings at the API boundary. A malformed id in a JWT or URL path raises a clean `400`/`401`, never an unhandled 500.
- **Dotted-field safety**: candidate decisions/feedback are keyed by email, which contains `.` — these are always written as a whole-dict `$set`, never as a dotted Mongo path built from the email, since Mongo would otherwise silently split the email's domain into a nested field.
- **Ownership/authorization** is enforced at the application layer on every read/write — e.g. `POST /plugin/evaluate` and the candidate-decision endpoints explicitly check the referenced outcome is owned by the caller before doing anything.

### Git history — action required

`backend/data/sql_app_v3.db` (pre-migration SQLite tables) and `backend/.env` (a real GitHub token and a Gemini API key) were committed to this repository in the past, while it was public on GitHub. Both secrets found in history were checked live and are already invalid/revoked, but the data itself is still in every clone's history until rewritten — **do not** treat "the file is gone from the working tree" as equivalent to "the data is gone."

---

## 📁 Project Structure

```
Recruvoskill/ (actual folder on disk still named SignalStack)
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── main.py                  # ASGI entrypoint
│   ├── app/
│   │   ├── main.py              # FastAPI app, Mongo lifespan, CORS, error handler, /health, router registration
│   │   ├── constants.py          # UserRole, JobRole
│   │   ├── config/database.py    # MongoDB client (PyMongo async), get_db dependency, index creation
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── routes/                # auth, outcome, candidate, evaluator, feedback, public (SEO), signal_extractor, task_decomposer
│   │   ├── deps/auth.py           # get_current_user / require_roles dependencies
│   │   ├── services/              # crud, auth, github, github_oauth, codeforces, leetcode, dsa_signals, llm, email, errors, mongo_errors, seo
│   │   ├── pipeline/               # signal_extractor, matcher, allocator, evaluator, task_decomposer, feedback
│   │   └── templates/job.html      # server-rendered public job page
│   ├── tests/                     # pytest suite
│   └── scripts/
│       ├── promote_admin.py
│       └── migrate_sqlite_to_mongodb.py   # one-time SQLite -> MongoDB data import
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── pages/                # AuthPage, GithubCallback, CandidateJobs, ProofSubmit, CandidateApplications,
│   │   │                         # Dashboard, OutcomeCreate, OutcomeDashboard, CandidateDecision, AdminAudit, FeedbackView
│   │   ├── context/AuthContext.jsx
│   │   ├── components/ProtectedRoute.jsx
│   │   ├── constants.js          # JOB_ROLES (mirrors backend JobRole)
│   │   └── api.js                # API client (attaches JWT, handles 401)
│   └── vercel.json               # SPA fallback + SEO route proxy to the backend
└── render.yaml
```

---

## 🧪 API Endpoints

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/auth/register` | Public — recruiter accounts only |
| POST | `/auth/register/candidate/start` | Public — starts GitHub-verified candidate signup |
| POST | `/auth/login` | Public |
| GET | `/auth/me` | Any authenticated user |
| POST | `/auth/forgot-password`, `/auth/reset-password` | Public |
| GET | `/auth/github/login` | Public — "Continue with GitHub" (candidates) |
| GET | `/auth/github/connect` | Any authenticated user |
| GET | `/auth/github/callback` | Public — GitHub's redirect target |
| POST | `/auth/github/confirm-email` | Public — email+username check before any OTP |
| POST | `/auth/github/verify-otp` | Public — completes login/signup/connect/register_verify |
| GET | `/job-roles` | Public |
| GET | `/outcomes`, `/outcomes/{id}` | Public (paginated, filterable by `job_role`) |
| POST | `/outcomes` | recruiter, admin |
| PUT | `/outcomes/{id}` | Owning recruiter, admin |
| GET | `/outcomes/{id}/candidates` | Owning recruiter, admin — the roster |
| GET | `/candidate/jobs` | Public (paginated, filterable by `job_role`) |
| GET | `/candidate/my-applications` | candidate (own data only — status + feedback, never a score) |
| GET`/PATCH` `/candidate/coding-profiles`, `POST .../refresh` | candidate |
| POST | `/proofs` | candidate |
| GET | `/proofs/{job_id}` | Owning recruiter, admin |
| POST | `/plugin/evaluate` | Owning recruiter, admin |
| GET | `/evaluations` | recruiter (own), admin (all) |
| GET | `/plugin/status/{job_id}` | Owning recruiter, admin |
| POST | `/evaluations/{job_id}/decision` | Owning recruiter, admin |
| POST | `/evaluations/{job_id}/feedback/suggest` | Owning recruiter, admin |
| POST | `/plugin/suggest-tasks` | recruiter, admin |
| GET | `/plugin/repo-preview` | Any authenticated user |
| POST | `/plugin/feedback` | recruiter, admin |
| GET | `/admin/audit-logs`, `/admin/signal-weights`, `/admin/feedback` | admin |
| GET | `/jobs/{id}/{slug}`, `/robots.txt`, `/sitemap.xml` | Public (SEO) |
| GET | `/health` | Public |

---

## 🔄 Migrating existing SQLite data

If you have a pre-migration `backend/data/sql_app.db` with real demo/dev data, import it once:

```bash
cd backend
venv/bin/python scripts/migrate_sqlite_to_mongodb.py data/sql_app.db
```

Safe to re-run — already-imported rows are skipped, not duplicated. Reports `inserted` / `skipped` / `failed` counts per collection. One-time tool, not something the running application depends on.

---

## 🎯 Roadmap

- [x] Core evaluation engine (deterministic signal matching, not an LLM call)
- [x] LLM-powered task decomposition
- [x] GitHub signal extraction + OAuth-verified candidate identity
- [x] Coding-platform signals (Codeforces, LeetCode)
- [x] Job-role tagging and filtering
- [x] Recruiter roster + per-candidate Advance/Reject decisions
- [x] AI-drafted, editable candidate feedback
- [x] Audit logging
- [x] User authentication (JWT, role-based authorization)
- [x] Public SEO-indexable job pages
- [x] MongoDB Atlas (migrated from SQLite/SQLAlchemy)
- [x] Dockerized local dev
- [ ] Wire the rubric weights (reliability/technical_depth/completeness) into the overall score — currently stored but not read by the scoring engine
- [ ] Multi-tenant support
- [ ] Webhook integrations
- [ ] MongoDB transactions for multi-document writes, if a future feature needs one

---

## 📄 License

MIT License

## 🙏 Acknowledgments

- Groq API for AI task decomposition and feedback drafting
- FastAPI for the backend framework
- React for the frontend framework
- Codeforces and LeetCode for their (official and unofficial, respectively) public data
