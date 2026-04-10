# Applyflow

Applyflow is a job-application workflow project with three active layers: a production Python CLI, a FastAPI backend, and a Bun-powered React frontend for the fullstack product.

Today the web product is internal-workspace-first: store your profile in the app, create jobs, score them from `0-100`, generate concise cover letters, manage statuses, and keep letters and task history inside the product database. The CLI still exists for local-file workflows and legacy exports, but the browser product now treats the database as the source of truth.

## What It Does

- scores a job description against your resume and context using the OpenAI Responses API
- returns a strict fit score with concise feedback
- generates a short, humanized cover letter
- keeps a database-backed internal job tracker and cover-letter library in the web app
- runs score and cover-letter tasks through background workers when Redis is configured
- keeps local archives of job descriptions, letters, and run metadata

## Workflow

1. Store your reusable profile in:
   - `data/profile/resume.md`
   - `data/profile/context.md`
2. Run `jobfit score`
3. Paste a job description
4. Receive:
   - score
   - verdict
   - concise feedback
   - cover letter
   - Google Doc link
   - updated Google Sheet row

## Why This Exists

The project was built for a real application workflow where the goal is not just to generate content, but to help make better decisions:

- honest fit evaluation, not flattery
- reusable candidate context across many applications
- one place to track jobs and statuses
- less manual copy-paste between AI output and application tracking

## Project Structure

```text
src/jobfit_cli/
  app.py              Main setup and scoring workflow
  cli.py              CLI entrypoint
  config.py           Environment and path loading
  constants.py        Shared defaults and sheet schema constants
  docs.py             Google Docs and Drive integration
  google_auth.py      Google OAuth and service-account auth helpers
  models.py           Compatibility exports for shared response models
  openai_service.py   Compatibility exports for shared OpenAI services
  prompts.py          Compatibility exports for shared prompt helpers
  sheets.py           Google Sheets logging, migration, and formatting
  storage.py          Local file persistence helpers

src/jobfit_core/
  models.py           Shared fit-evaluation schema
  prompts.py          Shared prompt builders and applicant-profile extraction
  openai_service.py   Shared OpenAI scoring and cover-letter generation
  workflows.py        Reusable job scoring workflow service

src/jobfit_api/
  main.py             FastAPI app entrypoint
  settings.py         API config and environment loading
  database.py         SQLAlchemy engine and session management
  models.py           Database models for the SaaS backend
  auth.py             Clerk-ready token verification helpers
  queue.py            Redis and Dramatiq broker setup
  task_processing.py  Phase 4 task creation and execution
  routes/             Health, auth, profile, jobs, and task API routes

frontend/
  package.json        Bun workspace for the React app
  src/app/            App root, providers, and TanStack Router setup
  src/pages/          Landing, dashboard, onboarding, jobs, detail, and settings pages
  src/lib/api/        OpenAPI-derived frontend contract and API client
  src/components/     Shared shell and UI primitives
  openapi.json        Exported backend OpenAPI schema for client generation

alembic/
  env.py              Alembic migration environment
  versions/           Database schema revisions

docker-compose.yml    Local Postgres and Redis services for API work

data/
  profile/            Reusable resume and context
  jobs/               Raw pasted job descriptions
  letters/            Local cover-letter backups
  runs/               JSON run metadata
  google/             OAuth token storage
```

## Requirements

- Python `3.14+`
- Bun `1.3+`
- an OpenAI API key
- for local API work: Docker or another Postgres/Redis setup

## Install

```bash
cd /path/to/project
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -e .
```

If your shell does not expose `pip`, use:

```bash
.venv/bin/python -m pip install -e .
```

## Configuration

Copy the example env file:

```bash
cp .env.example .env
```

Set these values in `.env`:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
FRONTEND_BASE_URL=http://127.0.0.1:5173
LOG_LEVEL=INFO
```

## First-Time Setup

Run:

```bash
jobfit setup
```

This will:

- create the local profile templates if needed
- validate OpenAI access
- run the Google OAuth browser login if needed
- validate Google Docs and Sheets access
- create or migrate the target sheet schema
- apply sheet formatting

Then fill in:

- `data/profile/resume.md`
- `data/profile/context.md`

## Backend API

The repo now includes Phases 1 through 4 of the fullstack backend plan:

- FastAPI app with `/` and `/api/v1/health`
- Clerk-ready bearer token verification hooks
- SQLAlchemy models for users, profiles, jobs, evaluations, cover letters, and background tasks
- Alembic migrations
- Redis and Dramatiq-backed task dispatch for out-of-process workers
- task retry metadata, manual retry support, and request-id based observability
- shared-core powered scoring and cover-letter generation from API task endpoints

The current API surface also includes the first real product routes:

- `GET /api/v1/profile`
- `POST /api/v1/profile`
- `PATCH /api/v1/profile`
- `GET /api/v1/jobs`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `PATCH /api/v1/jobs/{job_id}`
- `PATCH /api/v1/jobs/{job_id}/status`
- `GET /api/v1/cover-letters`
- `POST /api/v1/jobs/{job_id}/score`
- `POST /api/v1/jobs/{job_id}/cover-letter/regenerate`
- `GET /api/v1/tasks/{task_id}`
- `POST /api/v1/tasks/{task_id}/retry`

Current async note:
- score and cover-letter regeneration requests return a task id immediately
- when `REDIS_URL` is configured and a worker is running, execution happens out of process through Dramatiq
- when `REDIS_URL` is blank, local dev and tests fall back to in-process execution

### Run The API Locally

Start local Postgres and Redis:

```bash
docker compose up -d
```

Set these values in `.env` for local API work:

```env
DATABASE_URL=postgresql+psycopg://jobfit:jobfit@localhost:5432/jobfit
REDIS_URL=redis://localhost:6379/0
CLERK_ISSUER=your_clerk_issuer
CLERK_JWKS_URL=your_clerk_jwks_url
```

Apply migrations:

```bash
.venv/bin/python -m alembic upgrade head
```

Start the API:

```bash
jobfit-api
```

Start the worker in another terminal when `REDIS_URL` is configured:

```bash
python -m jobfit_api.worker
```

Then check:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

If you want to work without real auth during local backend setup, you can temporarily set:

```env
AUTH_ENABLED=false
```

Important note:
- `AUTH_ENABLED=false` is useful for boot and health checks
- protected product routes such as profile, jobs, and task polling still need a valid authenticated user context for meaningful manual testing

## Frontend App

The repo now includes Phases 5 through 7 of the fullstack plan:

- Bun-based frontend workspace in `frontend/`
- React 19 + Vite
- TanStack Router and TanStack Query
- Clerk wiring for browser auth
- onboarding, dashboard, jobs list, job detail, profile, letters, and settings pages
- OpenAPI-derived frontend API contract
- internal workspace flows for jobs, status tracking, task recovery, and cover letters

### Frontend Environment

Copy the example file:

```bash
cd frontend
cp .env.example .env
```

Set:

```env
VITE_API_BASE_URL=/api/v1
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

### Run The Frontend Locally

From the repo root, make sure the API is running first:

```bash
jobfit-api
```

In another terminal:

```bash
cd frontend
bun install
bun run generate:api
bun run dev
```

Then open:

```text
http://127.0.0.1:5173
```

Current frontend note:
- the frontend reads the backend OpenAPI schema into `frontend/src/lib/api/generated.ts`
- the shell is real for profile, jobs, detail, letters, and dashboard pages
- the browser now supports score and cover-letter regeneration actions from the job detail page
- failed tasks can now be retried directly from the job detail page
- the dashboard and jobs list now reflect latest evaluation and workflow state

## Staging Deployment

The repo now includes first-pass staging scaffolding for:

- API container image
- worker container image
- Render backend blueprint
- Vercel frontend routing config
- migration and startup scripts

Start with:

- [DEPLOYMENT.md](/Users/mhmd_ndri/Desktop/apply/DEPLOYMENT.md)
- [render.yaml](/Users/mhmd_ndri/Desktop/apply/render.yaml)
- [frontend/vercel.json](/Users/mhmd_ndri/Desktop/apply/frontend/vercel.json)

## Daily Usage

Run:

```bash
jobfit score
```

Paste the job description, then finish with `Ctrl-D`.

You can also pipe input:

```bash
pbpaste | jobfit score
```

The command now shows progress while it works:

- `Evaluating job fit...`
- `Generating cover letter...`
- `Creating Google Doc...`
- `Updating Google Sheet...`

## Outputs

For each scored job, the tool creates:

- a raw job archive in `data/jobs/`
- a local cover-letter backup in `data/letters/`
- a JSON run record in `data/runs/`
- a Google Doc for the cover letter
- a Google Sheets row for tracking

## Google Sheet Schema

The first worksheet is used as the tracker.

Current columns:

- `date`
- `company`
- `role_title`
- `application_status`
- `location`
- `source_url`
- `score`
- `verdict`
- `top_strengths_summary`
- `critical_gaps_summary`
- `feedback`
- `cover_letter_doc_url`
- `archived_job_path`
- `profile_hash`
- `model`

The sheet is formatted automatically with:

- frozen header row
- column sizing
- banded rows
- centered score cells
- score-based color highlighting
- status dropdown validation
- status color rules

## Application Status Options

- `wishlist`
- `applied`
- `waiting`
- `recruiter screen`
- `interview scheduled`
- `interviewing`
- `final round`
- `offer`
- `accepted`
- `rejected`
- `withdrawn`

## Cover Letter Behavior

The cover letter is designed to be:

- concise
- human
- grounded in the actual resume and context
- tailored to the role
- short enough to stay within a one-page document feel

The app also rebuilds the final letter structure itself so the output stays consistent:

- date
- greeting
- 3 short body paragraphs
- sign-off with your name

## OpenAI Model Behavior

Default model:

- `gpt-5.4-mini`

Fallback model:

- `gpt-4o-mini`

If your OpenAI project does not have access to `gpt-5.4-mini`, the app automatically retries with `gpt-4o-mini`.

## Security Notes

Sensitive files should not be committed.

This project already ignores:

- `.env`
- `.venv/`
- `credentials/`
- `data/`

That means your API keys, Google OAuth JSON, token file, and local run data are excluded by default.

If any secret was ever copied into a tracked file or pushed elsewhere, rotate it before publishing the repo.

## Publishing

Use this project as a single monorepo.

For the full GitHub workflow, including branch naming, safety checks, commit flow, generated OpenAPI files, and deployment-from-monorepo guidance, see:

- [GITHUB_MONOREPO_GUIDE.md](GITHUB_MONOREPO_GUIDE.md)

## Troubleshooting

### The app looks stuck after I press `Ctrl-D`

It may still be working through OpenAI, Google Docs, or Google Sheets calls. Recent versions print progress messages while they run.

### Google OAuth says access is blocked

Add your Gmail as a test user in the OAuth consent screen if the app is still in testing mode.

### Google Docs creation fails on personal Gmail with a service account

Use OAuth instead of a service account for personal Gmail Drive usage.

### The model returns invalid structured output

The app already includes output sanitization and a repair pass, but if the issue persists, inspect the run JSON in `data/runs/`.

## Documentation

For a full implementation report, architecture summary, setup history, and known limitations, see:

- [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md)
- [FULLSTACK_IMPLEMENTATION_PROMPT.md](FULLSTACK_IMPLEMENTATION_PROMPT.md)
- [FULLSTACK_IMPLEMENTATION_STATUS.md](FULLSTACK_IMPLEMENTATION_STATUS.md)
- [NEXT_THREAD_HANDOFF.md](NEXT_THREAD_HANDOFF.md)

## Test Commands

```bash
.venv/bin/python -m unittest discover -s tests
```

If you want to run the suite with an explicit source path:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
```

## License

No license file has been added yet. Add one before publishing publicly if you want reuse terms to be explicit.
