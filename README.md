# 🚀 SignaXAI - AI-Native Hiring Platform

**SignaXAI** is an AI-powered hiring platform that evaluates candidates based on real work artifacts (GitHub repositories) rather than resumes. It extracts objective signals from a candidate's repo (tests, CI/CD, ML models, deployment artifacts, etc.), scores them against a rubric, and surfaces the evidence behind every score.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![React](https://img.shields.io/badge/React-18+-61DAFB)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688)

---

## ✨ Features

### For Recruiters
- Define outcome-based job postings and let AI decompose them into verifiable tasks
- Trigger evaluations that score candidates against extracted GitHub signals
- Own and manage only the outcomes you created — enforced server-side, not just hidden in the UI

### For Candidates
- Browse public job postings without an account
- Register/log in, then submit a GitHub repo as proof of work
- View your own application status and score — never another candidate's

### Technical Features
- **Signal Extraction** — detects ML models, web frameworks, tests, deployment artifacts from a repo's file tree
- **Rule-based scoring engine** — task-to-signal matching and allocation (`app/pipeline/matcher.py`, `allocator.py`); this is deterministic, not an LLM call
- **AI task decomposition** — Groq (`openai/gpt-oss-120b`) turns a job description into verifiable tasks, with a rule-based fallback
- **JWT authentication with roles** — admin / recruiter / candidate, enforced on every protected endpoint
- **SEO-indexable public job pages** — server-rendered per-job pages with JobPosting structured data, `robots.txt`, `sitemap.xml`
- **Audit logging** — admin-visible log of outcome/proof/evaluation actions

---

## 🔐 Authentication & Roles

Auth is JWT-based (`POST /auth/register`, `POST /auth/login`, `GET /auth/me`). Passwords are hashed with bcrypt; tokens are signed with `JWT_SECRET_KEY` and expire after `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default 60).

| Role | Can do |
|------|--------|
| **candidate** | Browse public jobs, submit proofs, view *only their own* applications/scores |
| **recruiter** | Create outcomes, evaluate candidates, view proofs/evaluations *for outcomes they own* |
| **admin** | Everything a recruiter can do across all outcomes, plus audit logs and signal-weight config |

Self-registration (`POST /auth/register`) only ever creates `candidate` or `recruiter` accounts — `admin` cannot be granted through the public API. To create the first admin:

```bash
cd backend
venv/bin/python scripts/promote_admin.py you@example.com   # after registering that account normally
```

Every authorization rule above is enforced in the backend (`app/deps/auth.py`, ownership checks in each route) — the frontend's route guards (`ProtectedRoute`) are a UX convenience only, not a security boundary.

**Candidate identity**: a candidate's identity comes from their JWT, never from a client-supplied id or email. `POST /proofs` overwrites whatever `candidate_id` the client sends with the authenticated user's email server-side, and `GET /candidate/my-applications` takes no id parameter at all — it can only ever return the caller's own data.

**Forgot password**: `POST /auth/forgot-password` (email) → `POST /auth/reset-password` (email, 6-digit OTP, new password). The OTP is a random 6-digit code, hashed (sha256) before being stored, valid for `PASSWORD_RESET_OTP_EXPIRE_MINUTES` (default 10), single-use, capped at `PASSWORD_RESET_MAX_ATTEMPTS` wrong guesses (default 5), and rate-limited to one request per `PASSWORD_RESET_COOLDOWN_SECONDS` (default 60) per email. `forgot-password` always returns the same generic message regardless of whether the email is registered, so it can't be used to enumerate accounts. **Requires SMTP configuration** (`SMTP_HOST`/`SMTP_USER`/`SMTP_PASSWORD` in `.env`) to actually deliver the email — without it, the code is only written to the server log (development convenience, not something to rely on in production). See `.env.example` for the full SMTP variable list.

**GitHub verification**: candidates must connect a real GitHub account via OAuth (`GET /auth/github/login` to sign up/in with GitHub directly, or `GET /auth/github/connect` — authenticated — to link GitHub to an existing email/password account) before they can submit a proof. `POST /proofs` is blocked with a 403 until `github_username` is set on the account, and further checks that the submitted `repo_url`'s owner matches that verified username — a candidate can never submit someone else's repo, or claim a GitHub identity that isn't theirs. One SignaXAI account can link at most one GitHub account and vice versa (enforced by a partial unique index on `users.github_id`); if a GitHub account is already linked elsewhere, `/auth/github/connect` refuses rather than silently reassigning it. A GitHub-only signup with no matching existing account gets a `hashed_password: null` account — email/password login is correctly rejected for it (`verify_password` treats a missing hash as "never matches", not a crash). **Requires a registered GitHub OAuth App** (`GITHUB_OAUTH_CLIENT_ID`/`GITHUB_OAUTH_CLIENT_SECRET` in `.env`, created at github.com/settings/developers with callback URL `{PUBLIC_BASE_URL}/auth/github/callback`) — without it, the GitHub routes return `503`, not a crash.

---

## 🌐 Public SEO Job Pages

Because the frontend is a client-rendered Vite SPA, its routes aren't crawlable — a search engine would see an empty `<div id="root">`. Rather than migrating the whole app to a new framework, the backend serves a small set of server-rendered public pages directly (Jinja2, `app/templates/job.html`):

- `GET /jobs/{outcome_id}` → 301 to the canonical slug URL
- `GET /jobs/{outcome_id}/{slug}` → full HTML page: title, description, tasks, `<link rel="canonical">`, Open Graph tags, and `schema.org/JobPosting` JSON-LD
- `GET /robots.txt`, `GET /sitemap.xml` → only outcomes with `is_public=true`

In production, `frontend/vercel.json` proxies `/jobs/*`, `/robots.txt`, and `/sitemap.xml` from the frontend's domain to this backend, so crawlers see one consistent public domain. **You must replace `YOUR-BACKEND-DOMAIN.onrender.com` in `frontend/vercel.json` with your actual deployed backend URL** — this can't be known until you've deployed once.

**Limitation**: the JobPosting schema always sets `jobLocationType: TELECOMMUTE` / `employmentType: CONTRACTOR` as a reasonable default, since outcomes don't currently model location or employment type. Add those fields to the `Outcome` model if you need them to vary per posting.

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────────┐
│   React Frontend │────▶│  FastAPI Backend │────▶│  MongoDB Atlas   │
│   (Vite + JSX)   │     │   (Python 3.10)  │     │  (PyMongo async) │
└─────────────────┘     └────────┬─────────┘     └──────────────────┘
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
              ┌─────────┐  ┌──────────┐  ┌─────────┐
              │ GitHub  │  │  Groq    │  │ Signal  │
              │   API   │  │   LLM    │  │ Engine  │
              └─────────┘  └──────────┘  └─────────┘
```

The backend talks to MongoDB via PyMongo's native async API (`pymongo.AsyncMongoClient` — no Motor). One client is created at FastAPI startup (`lifespan`) and reused for every request; it's closed cleanly on shutdown.

---

## 🚀 Local Setup

### Prerequisites
- Python 3.10+
- Node.js 18+
- A MongoDB Atlas account (or a local `mongod` for development — see below)
- A GitHub token (repo analysis) and a Groq API key (AI task decomposition) — the app runs without them but falls back to reduced/mock behavior

### MongoDB Atlas setup

1. Create a free cluster at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas).
2. **Database Access** → add a database user (username + password).
3. **Network Access** → add your current IP (or `0.0.0.0/0` for unrestricted dev access — never do this in production).
4. **Database → Connect → Drivers** → copy the `mongodb+srv://...` connection string.

You don't have to use Atlas for local development — pointing `MONGODB_URI` at a local `mongod` (`mongodb://localhost:27017`) works identically, since both go through the same PyMongo async driver code path. Atlas is what production should use.

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env: at minimum set MONGODB_URI, GROQ_API_KEY, GITHUB_TOKEN, JWT_SECRET_KEY
# (generate a JWT secret with: python -c "import secrets; print(secrets.token_hex(32))")
# MONGODB_URI defaults to mongodb://localhost:27017 if unset in development.

uvicorn main:app --reload
```

Indexes are created automatically on startup (see `app/config/database.py: _ensure_indexes`) — no separate migration step needed for the schema itself.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Access
- Frontend: http://localhost:5173
- Backend API + docs: http://localhost:8000 / http://localhost:8000/docs

---

## 🧪 Tests

```bash
cd backend
venv/bin/python -m pytest -q
```

Tests run against `MONGODB_TEST_DATABASE` (`signaxai_test` by default), never your real `MONGODB_DATABASE` — `tests/conftest.py` forces `ENVIRONMENT=test`, and `config.MONGODB_ACTIVE_DATABASE` always resolves to the test database whenever that's set, regardless of what else is configured. Collections are truncated before every test. This needs a reachable MongoDB (local `mongod` or Atlas) at `MONGODB_URI` — tests don't spin up their own server. Coverage includes: registration/login/JWT validation, role-based authorization, cross-user/cross-recruiter access denial (IDOR), outcome/proof/evaluation flows, CORS, invalid ObjectId handling, duplicate-key handling, and production error-response shape.

Frontend build check:

```bash
cd frontend
npm run build
```

`npm run lint` currently fails independent of this work — `eslint.config.js` uses the ESLint 9 flat-config API (`eslint/config`) but `package.json` pins ESLint 8.57, which doesn't export it. Fixing this needs an ESLint major-version bump and is left as a follow-up.

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
CORS_ORIGINS=http://localhost:5173,http://localhost:5175
GITHUB_TOKEN=
GROQ_API_KEY=
PUBLIC_BASE_URL=http://localhost:8000
FRONTEND_BASE_URL=http://localhost:5173
```

`GITHUB_TOKEN`, `GROQ_API_KEY`, and `MONGODB_URI` are backend-only and are never exposed to the browser — the frontend only ever receives `VITE_API_BASE_URL`. Never put a real `MONGODB_URI` (it contains credentials) into source code, this README, `.env.example`, or a Vite `VITE_*` variable.

---

## 🛡️ Security Notes

- **CORS** is an explicit allowlist (`CORS_ORIGINS`), never `*` — required, since the API uses credentialed requests.
- **Errors**: in production (`ENVIRONMENT=production`), unhandled exceptions return `{"detail": "Internal server error", "request_id": "..."}` — no stack traces, file paths, or internal messages reach the client. Full detail is logged server-side against the same `request_id`.
- **GitHub URL handling**: only `github.com` hosts are accepted; the backend never fetches an arbitrary URL a client supplies (guards against SSRF via the repo-analysis feature).
- **Upstream failures** (GitHub/Groq) return categorized, machine-readable errors (`{"error": "RATE_LIMIT", "service": "github", "retryable": true, ...}`) instead of raw exception text or a silently faked result — unless `DEMO_MODE=true`.
- **Database errors**: PyMongo exceptions are never returned to clients. `app/services/mongo_errors.py` maps them to clean responses — e.g. a duplicate-key error becomes `409 {"detail": "Resource already exists."}`, never the raw `E11000 duplicate key error collection: ...` message. The real exception is always logged server-side only.
- **ObjectId handling**: Mongo `_id` values are converted to plain strings at the API boundary (`id: "..."`); the frontend never sees a raw `ObjectId`. A malformed id in a JWT or URL path raises a clean `400`/`401`, never an unhandled `bson.errors.InvalidId` 500.
- **Ownership/authorization** is enforced at the application layer on every read/write — Mongo doesn't enforce relationships the way SQL foreign keys did, so e.g. `POST /plugin/evaluate` explicitly checks the referenced outcome exists and is owned by the caller before doing anything.

### Git history — action required

`backend/data/sql_app_v3.db` (containing the pre-migration SQLite tables: `outcomes`, `proofs`, `evaluations`, `feedback`, `audit_logs`) and `backend/.env` (containing a real GitHub token and a Gemini API key) were committed to this repository in the past, while it was public on GitHub. Both secrets found in history were checked live and are already invalid/revoked, but the data itself is still in every clone's history until rewritten. See the project maintainer's notes for the exact `git filter-repo` commands and required follow-up — **do not** treat "the file is gone from the working tree" as equivalent to "the data is gone." This applies regardless of the MongoDB migration — the SQLite file's history doesn't get cleaner just because the app no longer reads it.

---

## 📁 Project Structure

```
SignalStack/
├── backend/
│   ├── main.py                  # ASGI entrypoint
│   ├── app/
│   │   ├── main.py              # FastAPI app, Mongo lifespan, CORS, error handler, /health, router registration
│   │   ├── constants.py          # UserRole
│   │   ├── config/database.py    # MongoDB client (PyMongo async), get_db dependency, index creation
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   ├── routes/                # auth, outcome, candidate, evaluator, feedback, public (SEO), signal_extractor, task_decomposer
│   │   ├── deps/auth.py           # get_current_user / require_roles dependencies
│   │   ├── services/              # crud (Mongo queries), auth (hashing/JWT), github, llm, errors, mongo_errors, seo
│   │   ├── pipeline/               # signal_extractor, matcher, allocator, evaluator, task_decomposer, feedback
│   │   └── templates/job.html      # server-rendered public job page
│   ├── tests/                     # pytest suite (auth, authorization, outcomes, proofs, evaluations, security)
│   └── scripts/
│       ├── promote_admin.py
│       └── migrate_sqlite_to_mongodb.py   # one-time SQLite -> MongoDB data import
├── frontend/
│   ├── src/
│   │   ├── pages/                # React page components (Login, Register, Dashboard, ...)
│   │   ├── context/AuthContext.jsx
│   │   ├── components/ProtectedRoute.jsx
│   │   └── api.js                # API client (attaches JWT, handles 401)
│   └── vercel.json               # SPA fallback + SEO route proxy to the backend
└── render.yaml
```

---

## 🧪 API Endpoints

| Method | Endpoint | Auth |
|--------|----------|------|
| POST | `/auth/register` | Public |
| POST | `/auth/login` | Public |
| GET | `/auth/me` | Any authenticated user |
| POST | `/auth/forgot-password` | Public — always returns a generic message |
| POST | `/auth/reset-password` | Public — requires a valid OTP sent to the account's email |
| GET | `/auth/github/login` | Public — redirects to GitHub; logs in or creates a candidate account |
| GET | `/auth/github/connect` | Any authenticated user — returns `{authorize_url}` to link GitHub |
| GET | `/auth/github/callback` | Public — GitHub's redirect target, not called directly |
| GET | `/outcomes`, `/outcomes/{id}` | Public (paginated) |
| POST | `/outcomes` | recruiter, admin |
| PUT | `/outcomes/{id}` | Owning recruiter, admin |
| GET | `/candidate/jobs` | Public (paginated) |
| GET | `/candidate/my-applications` | candidate (own data only) |
| POST | `/proofs` | candidate |
| GET | `/proofs/{job_id}` | Owning recruiter, admin |
| POST | `/plugin/evaluate` | Owning recruiter, admin |
| GET | `/evaluations` | recruiter (own), admin (all) — paginated |
| GET | `/plugin/status/{job_id}` | Owning recruiter, admin |
| POST | `/plugin/suggest-tasks` | recruiter, admin |
| GET | `/plugin/repo-preview` | Any authenticated user |
| POST | `/plugin/feedback` | recruiter, admin |
| GET | `/admin/audit-logs`, `/admin/signal-weights`, `/admin/feedback` | admin |
| GET | `/jobs/{id}/{slug}`, `/robots.txt`, `/sitemap.xml` | Public, unauthenticated (SEO) |
| GET | `/health` | Public — `{"status": "ok", "database": "connected"}`, never leaks the connection string or a raw driver error |

---

## 🔄 Migrating existing SQLite data

If you have a pre-migration `backend/data/sql_app.db` with real demo/dev data, import it once:

```bash
cd backend
venv/bin/python scripts/migrate_sqlite_to_mongodb.py data/sql_app.db
```

It's safe to re-run — already-imported rows are skipped, not duplicated (see the script's docstring for the exact matching key per collection). It reports `inserted` / `skipped` / `failed` counts per collection. This script is a one-time tool, not something the running application depends on.

---

## 🎯 Roadmap

- [x] Core evaluation engine
- [x] LLM-powered task decomposition
- [x] GitHub signal extraction
- [x] Audit logging
- [x] User authentication (JWT, role-based authorization)
- [x] Public SEO-indexable job pages
- [x] Anonymized review mode (frontend toggle in Reviewer Queue)
- [x] MongoDB Atlas (migrated from SQLite/SQLAlchemy)
- [ ] Multi-tenant support
- [ ] Webhook integrations
- [ ] MongoDB transactions for multi-document writes, if a future feature needs one (nothing today writes to more than one collection atomically — proof submission and evaluation creation are each a single insert)

---

## 📄 License

MIT License

## 🙏 Acknowledgments

- Groq API for AI task decomposition
- FastAPI for the backend framework
- React for the frontend framework
