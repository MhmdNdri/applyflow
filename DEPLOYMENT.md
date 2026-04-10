# Applyflow Deployment Guide

This repo can now deploy in two shapes:

1. **Free/staging demo mode:** frontend on Vercel, API on Vercel, Neon Postgres, no Redis, no worker.
2. **Production worker mode:** frontend on Vercel, API and worker on a backend host, Neon/Postgres, Redis.

Use demo mode while the product is still moving quickly. Move to worker mode when scoring tasks need stronger reliability, retries, and longer execution time.

## Repo Deployment Files

- [api/index.py](/Users/mhmd_ndri/Desktop/apply/api/index.py) exposes the FastAPI app to Vercel.
- [vercel.json](/Users/mhmd_ndri/Desktop/apply/vercel.json) routes API traffic to the Vercel Python function.
- [frontend/vercel.json](/Users/mhmd_ndri/Desktop/apply/frontend/vercel.json) keeps frontend SPA routing working.
- [Dockerfile.api](/Users/mhmd_ndri/Desktop/apply/Dockerfile.api) is for container API hosting.
- [Dockerfile.worker](/Users/mhmd_ndri/Desktop/apply/Dockerfile.worker) is for container worker hosting.
- [render.yaml](/Users/mhmd_ndri/Desktop/apply/render.yaml) is the optional Render blueprint.

## Option A: Free Vercel Demo Mode

This is the cheapest way to get the app online.

Architecture:

- Vercel project 1: `applyflow-web`
- Vercel project 2: `applyflow-api`
- Neon free Postgres
- Clerk auth
- OpenAI API
- `REDIS_URL` blank
- `TASK_EXECUTION_MODE=inline`

Important tradeoff:

- The score request runs inside the API request instead of a separate worker.
- The browser still receives a task id and polls normally.
- This is good for demos and personal staging, but not ideal for heavy public traffic.

### 1. Deploy The Frontend On Vercel

Create a Vercel project from the GitHub repo.

Set:

```text
Root Directory: frontend
Application Preset: Vite
Build Command: bun run build
Output Directory: dist
Install Command: bun install
```

Frontend environment variables:

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_test_or_live_...
VITE_API_BASE_URL=https://your-api-project.vercel.app/api/v1
```

If the API project does not exist yet, add a temporary placeholder and update it after deploying the API.

### 2. Deploy The API On Vercel

Create a second Vercel project from the same GitHub repo.

Set:

```text
Root Directory: .
Application Preset: Other
```

If Vercel detects Python/FastAPI automatically, that is fine too. The important part is that this project uses the repo root, not `frontend`.

API environment variables:

```env
APP_ENV=staging
API_PREFIX=/api/v1
API_TITLE=Applyflow API
API_VERSION=0.1.0
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=
TASK_EXECUTION_MODE=inline
AUTH_ENABLED=true
LOG_LEVEL=INFO
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=
CLERK_AUTHORIZED_PARTY=
FRONTEND_BASE_URL=https://your-frontend-project.vercel.app
CORS_ALLOWED_ORIGINS=https://your-frontend-project.vercel.app
```

Do not put frontend-only variables such as `VITE_CLERK_PUBLISHABLE_KEY` in the API project unless you specifically need them there.

### 3. Run Database Migrations

Vercel will not run Alembic migrations for you. Run migrations from your local machine against the Neon database:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
python -m alembic upgrade head
```

Make sure your local `.env` has the same `DATABASE_URL` as the deployed API when you run this.

### 4. Wire The Frontend To The API

After the API deploy succeeds, copy the API Vercel URL into the frontend project:

```env
VITE_API_BASE_URL=https://your-api-project.vercel.app/api/v1
```

Redeploy the frontend.

### 5. Smoke Test Demo Mode

Check API health:

```bash
curl https://your-api-project.vercel.app/api/v1/health
```

Expected:

- `database.status` is `ok`
- `redis.status` is `not_configured`
- `task_executor.detail` is `TASK_EXECUTION_MODE=inline`

Then open the frontend:

1. Sign in with Clerk.
2. Create or update your profile.
3. Create a job.
4. Click score/regenerate.
5. Wait for the request to finish and confirm the task becomes completed.

## Option B: Production Worker Mode

Use this when you are ready to pay for a backend host and want a more reliable architecture.

Architecture:

- Vercel frontend
- Render/Railway/Fly/EC2 API service
- Render/Railway/Fly/EC2 worker service
- Neon/Postgres
- Redis

Backend environment variables for both API and worker:

```env
APP_ENV=production
LOG_LEVEL=INFO
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
TASK_EXECUTION_MODE=background
AUTH_ENABLED=true
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=
CLERK_AUTHORIZED_PARTY=
```

API-only environment variables:

```env
FRONTEND_BASE_URL=https://your-frontend-domain.vercel.app
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
```

The API service should run:

```bash
./scripts/start_api.sh
```

The worker service should run:

```bash
./scripts/start_worker.sh
```

Run migrations before sending real traffic:

```bash
./scripts/run_migrations.sh
```

## Local Pre-Deploy Checks

From the repo root:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
python -m unittest discover -s tests
```

Frontend:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun run generate:api
bun test
bun run build
```

## Current Limits

- Vercel demo mode has no Redis worker and no delayed retry queue.
- OpenAI usage is still paid even if hosting is free.
- Long scoring requests can hit Vercel function duration limits.
- The browser product stores cover letters internally in the database.
- The legacy CLI still contains Google Docs/Sheets export behavior, but the web product does not require Google access.
