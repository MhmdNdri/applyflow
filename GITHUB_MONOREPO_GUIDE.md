# Applyflow GitHub Monorepo Guide

Use **one GitHub repository** for Applyflow.

This project is a good fit for a monorepo because the frontend, backend, worker, migrations, shared AI core, and CLI all evolve together.

## Recommended Repo Shape

Keep this structure in one repo:

```text
applyflow/
  frontend/                 React + Bun web app
  src/jobfit_api/           FastAPI backend
  src/jobfit_core/          Shared AI/domain logic
  src/jobfit_cli/           CLI workflow
  alembic/                  Database migrations
  scripts/                  Start, migration, and OpenAPI scripts
  tests/                    Backend and core tests
  Dockerfile.api            API container
  Dockerfile.worker         Worker container
  render.yaml               Render backend/worker blueprint
  docker-compose.yml        Local Postgres/Redis
  DEPLOYMENT.md             Deployment runbook
  README.md                 Public project overview
```

## Why Monorepo

Use one repo because:

- the frontend depends on the backend OpenAPI schema
- the API, worker, and migrations must deploy together
- `jobfit_core` is shared by CLI and API
- one PR can update backend, frontend, migrations, docs, and tests together
- Render and Vercel can deploy different folders/services from the same repo

Do not split into separate repos unless separate teams eventually own frontend/backend independently.

## What Must Never Be Pushed

These paths should stay untracked:

```text
.env
.venv/
credentials/
data/
frontend/node_modules/
frontend/dist/
frontend/.tanstack/
*.egg-info/
```

Your current [.gitignore](/Users/mhmd_ndri/Desktop/apply/.gitignore) already covers these.

Before pushing, always check:

```bash
git status --short
```

If you see any of these staged, stop and unstage them:

```bash
git restore --staged .env credentials data .venv frontend/node_modules frontend/dist
```

## Pre-Push Checklist

From the repo root:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
python -m alembic upgrade head
python -m unittest discover -s tests
```

Then frontend:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun run generate:api
bun test
bun run build
```

If all pass, go back to the repo root:

```bash
cd /Users/mhmd_ndri/Desktop/apply
git status --short
```

## Safe Push Flow

Use this flow for normal work:

```bash
cd /Users/mhmd_ndri/Desktop/apply
git status --short
git add .
git status --short
```

Review the staged files carefully.

Then commit:

```bash
git commit -m "Add fullstack staging and hardening groundwork"
```

Push:

```bash
git push origin main
```

## Better Branch Flow

For larger work, use feature branches:

```bash
cd /Users/mhmd_ndri/Desktop/apply
git switch -c codex/phase-8-hardening
git add .
git commit -m "Harden task retries and staging deployment"
git push -u origin codex/phase-8-hardening
```

Then open a pull request on GitHub.

Recommended branch naming:

```text
codex/<short-feature-name>
```

Examples:

```text
codex/frontend-polish
codex/staging-deployment
codex/task-watchdog
codex/rate-limits
```

## Deployment From The Monorepo

Use the same GitHub repo for all deployments.

### Vercel Frontend

Create a Vercel project from the repo.

Set:

```text
Root Directory: frontend
```

Environment variables:

```env
VITE_API_BASE_URL=https://your-api-domain.onrender.com/api/v1
VITE_CLERK_PUBLISHABLE_KEY=pk_...
```

### Render Backend

Use [render.yaml](/Users/mhmd_ndri/Desktop/apply/render.yaml).

It creates:

- API web service from [Dockerfile.api](/Users/mhmd_ndri/Desktop/apply/Dockerfile.api)
- worker service from [Dockerfile.worker](/Users/mhmd_ndri/Desktop/apply/Dockerfile.worker)

Both services should use the same:

```env
DATABASE_URL=...
REDIS_URL=...
OPENAI_API_KEY=...
CLERK_ISSUER=...
CLERK_JWKS_URL=...
```

## Migration Rule

If a commit changes files under:

```text
alembic/
src/jobfit_api/models.py
```

then run migrations before smoke-testing:

```bash
python -m alembic upgrade head
```

For deployed environments, run:

```bash
./scripts/run_migrations.sh
```

## OpenAPI Rule

If backend API schemas or routes change, regenerate frontend types:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun run generate:api
```

Commit these generated files when they change:

```text
frontend/openapi.json
frontend/src/lib/api/generated.ts
```

## Commit Message Examples

Good commit messages:

```text
Add worker-backed task retries
Add internal cover letter library
Add staging deployment scaffolding
Fix application status enum persistence
Polish job detail workflow recovery UI
```

Avoid vague messages like:

```text
updates
fix stuff
changes
```

## Before Making The Repo Public

Run:

```bash
git grep -n "sk-" || true
git grep -n "npg_" || true
git grep -n "CLERK_SECRET_KEY" || true
git grep -n "BEGIN PRIVATE KEY" || true
```

If anything secret-like appears, remove it and rotate the secret before pushing.

Also check:

```bash
git status --ignored --short
```

You should see ignored local-only paths like `.env`, `credentials/`, and `data/`, but they should not be staged.

## Current Remote

The repo currently points to:

```text
https://github.com/MhmdNdri/applyflow.git
```

Check any time with:

```bash
git remote -v
```

