# Applyflow Deployment Guide

This guide covers the recommended staging setup for the current Applyflow architecture:

- frontend on Vercel
- API on Render
- worker on Render
- Postgres on Neon
- Redis on Upstash or Render Redis

The repo already includes:

- [Dockerfile.api](/Users/mhmd_ndri/Desktop/apply/Dockerfile.api)
- [Dockerfile.worker](/Users/mhmd_ndri/Desktop/apply/Dockerfile.worker)
- [render.yaml](/Users/mhmd_ndri/Desktop/apply/render.yaml)
- [frontend/vercel.json](/Users/mhmd_ndri/Desktop/apply/frontend/vercel.json)
- [scripts/start_api.sh](/Users/mhmd_ndri/Desktop/apply/scripts/start_api.sh)
- [scripts/start_worker.sh](/Users/mhmd_ndri/Desktop/apply/scripts/start_worker.sh)
- [scripts/run_migrations.sh](/Users/mhmd_ndri/Desktop/apply/scripts/run_migrations.sh)

## Deployment Shape

Use three deployed services:

1. `applyflow-web`
   - Vercel project
   - root directory: `frontend`
   - static SPA build

2. `applyflow-api-staging`
   - Render web service
   - Docker runtime
   - serves the FastAPI app

3. `applyflow-worker-staging`
   - Render worker service
   - Docker runtime
   - runs Dramatiq jobs for score and cover-letter tasks

Shared managed services:

- Neon Postgres
- Redis

## Backend Environment Variables

Set these on both the API and worker:

```env
APP_ENV=staging
LOG_LEVEL=INFO
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.4-mini
DATABASE_URL=postgresql+psycopg://...
REDIS_URL=redis://...
AUTH_ENABLED=true
CLERK_ISSUER=https://your-clerk-domain.clerk.accounts.dev
CLERK_JWKS_URL=https://your-clerk-domain.clerk.accounts.dev/.well-known/jwks.json
CLERK_AUDIENCE=
CLERK_AUTHORIZED_PARTY=
```

Set these on the API service too:

```env
FRONTEND_BASE_URL=https://your-frontend-domain.vercel.app
CORS_ALLOWED_ORIGINS=https://your-frontend-domain.vercel.app
```

Optional:

```env
API_TITLE=Applyflow API
API_VERSION=0.1.0
API_PREFIX=/api/v1
```

## Frontend Environment Variables

Set these on Vercel:

```env
VITE_CLERK_PUBLISHABLE_KEY=pk_live_or_test_...
VITE_API_BASE_URL=https://your-api-domain.onrender.com/api/v1
```

## Render Setup

### Option A: Use The Blueprint

1. Push this repo to GitHub.
2. In Render, create a new Blueprint from the repo.
3. Render will detect [render.yaml](/Users/mhmd_ndri/Desktop/apply/render.yaml).
4. Fill in all `sync: false` environment variables.
5. Deploy both services.

### Option B: Create Services Manually

Create the API service:

- runtime: Docker
- dockerfile: [Dockerfile.api](/Users/mhmd_ndri/Desktop/apply/Dockerfile.api)
- health check path: `/api/v1/health`

Create the worker service:

- runtime: Docker
- dockerfile: [Dockerfile.worker](/Users/mhmd_ndri/Desktop/apply/Dockerfile.worker)

### Run Migrations

Before treating staging as healthy, run:

```bash
python -m alembic upgrade head
```

If your provider gives you a shell inside the API image, run:

```bash
./scripts/run_migrations.sh
```

Run migrations:

- after the first deploy
- after every schema-changing release
- before sending real traffic to a fresh environment

## Vercel Setup

1. Create a Vercel project from the repo.
2. Set the project root directory to:

```text
frontend
```

3. Keep the default Vite build behavior.
4. Add the frontend environment variables.
5. Deploy.

The SPA routing rewrite is already handled by [frontend/vercel.json](/Users/mhmd_ndri/Desktop/apply/frontend/vercel.json).

## Staging Smoke Test

After deployment:

1. Check the API health route:

```bash
curl https://your-api-domain.onrender.com/api/v1/health
```

Expected:

- database `ok`
- redis `ok`

2. Open the frontend.
3. Sign in with Clerk.
4. Create or update a profile.
5. Create a job.
6. Click `Score this job`.
7. Confirm:
   - task becomes `queued`
   - worker picks it up
   - task becomes `completed`
   - evaluation appears
   - cover letter appears

8. If possible, force a failing task in staging or a preview environment and verify:
   - the task shows `failed`
   - retry is available
   - retry can recover the job detail flow

## Operational Checklist

Before each deploy:

- run:
  - `python -m unittest discover -s tests`
  - `cd frontend && bun test`
  - `cd frontend && bun run build`
- check the migration diff
- make sure the API and worker share the same environment values

After each deploy:

- run migrations if needed
- verify `/api/v1/health`
- verify one end-to-end score task
- verify worker logs show task execution

## Rollback Strategy

If a deployment breaks:

1. Roll back the frontend first if the issue is browser-only.
2. Roll back the API and worker together if the issue is backend/runtime related.
3. If the release included a migration:
   - prefer forward-fixing unless the migration is known-safe to reverse
   - do not drop production data casually

## Current Limits

- The browser product is internal-workspace-first and no longer depends on Google integrations.
- The CLI still contains legacy Google export behavior, but that is separate from the deployed browser product.
- Worker mode requires Redis. Without Redis, the API falls back to in-process task execution, which is only meant for local development.
