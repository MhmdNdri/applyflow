# Applyflow

Applyflow is an AI-powered job application cockpit for individual job seekers.

It helps you keep one honest profile, paste job descriptions, score fit from `0-100`, generate concise cover letters, and track every application in a private internal workspace.

## What It Does

- Scores each role against your resume and context.
- Generates a warm, concise, tailored cover letter.
- Tracks jobs by company, role, score, status, and date.
- Stores cover letters inside the app instead of requiring Google Docs.
- Keeps profile, job, evaluation, cover-letter, and task data in Postgres.
- Supports async scoring with Redis workers, plus an inline Vercel demo mode.
- Preserves the original Python CLI for local workflows.

## Stack

- Backend: FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL.
- AI: OpenAI Responses API, defaulting to `gpt-5.4-mini` with fallback support.
- Jobs: Dramatiq and Redis for worker-backed task execution.
- Auth: Clerk.
- Frontend: React, Vite, Bun, TypeScript, TanStack Router, TanStack Query, TanStack Table.
- Deployment: Vercel for the frontend; Vercel demo mode or container worker mode for the API.

## Project Structure

```text
applyflow/
  alembic/                Database migrations
  frontend/               React web app
  scripts/                API, worker, and migration start scripts
  src/jobfit_api/         FastAPI backend
  src/jobfit_cli/         Local CLI
  src/jobfit_core/        Shared scoring and cover-letter logic
  tests/                  Backend and core tests
  DEPLOYMENT.md           Deployment guide
  Dockerfile.api          API container image
  Dockerfile.worker       Worker container image
  index.py                Vercel FastAPI entrypoint
  render.yaml             Optional Render blueprint
```

## Quick Start

Create and activate the Python environment:

```bash
cd /Users/mhmd_ndri/Desktop/apply
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install -e .
```

Create your environment file:

```bash
cp .env.example .env
```

Set at least:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
DATABASE_URL=postgresql+psycopg://...
AUTH_ENABLED=true
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json
```

Apply migrations:

```bash
.venv/bin/python -m alembic upgrade head
```

Run the API:

```bash
jobfit-api
```

Check health:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

## Frontend

Install and run the web app:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun install
cp .env.example .env
bun run generate:api
bun run dev
```

For local development, `frontend/.env` usually uses:

```env
VITE_API_BASE_URL=/api/v1
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
```

Open:

```text
http://127.0.0.1:5173
```

## Task Execution

Applyflow supports two task modes:

- `TASK_EXECUTION_MODE=background`: use Redis and a Dramatiq worker for production-shaped async processing.
- `TASK_EXECUTION_MODE=inline`: run scoring inside the API request, useful for free Vercel demo deployments without Redis.

For worker mode, run the worker in another terminal:

```bash
jobfit-worker
```

## CLI

The CLI is still available for local scoring:

```bash
jobfit score
```

Paste a job description, then finish with `Ctrl-D`.

The CLI can also keep local archives under `data/`. Legacy Google Docs and Sheets export behavior remains in the CLI only when configured.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md).

Supported deployment shapes:

- Free demo: frontend on Vercel, API on Vercel, Neon Postgres, no Redis.
- Production-shaped: frontend on Vercel, API and worker containers, Postgres, Redis.

## Testing

Backend and core tests:

```bash
.venv/bin/python -m unittest discover -s tests
```

Frontend checks:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun test
bun run build
```

## Security

Do not commit secrets or local runtime data.

Ignored by default:

- `.env`
- `.venv/`
- `credentials/`
- `data/`
- `frontend/.env`
- `frontend/node_modules/`

If any real secret was ever committed or pasted publicly, rotate it before publishing.

## License

No license has been added yet.
