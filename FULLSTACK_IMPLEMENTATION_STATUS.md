# Applyflow Fullstack Implementation Status

Last updated: 2026-04-03

## Purpose

This document is the implementation record for the fullstack `applyflow` project.

It is not the original roadmap prompt. It is the current reality of the repository:

- what exists
- what has been verified
- what still needs work
- how to run and test the project locally

This repo started as a Python CLI for job-fit scoring and cover-letter generation. It is now evolving into a fullstack SaaS, while keeping the CLI alive as the stable working interface.

## Current Status

Completed phases:
- Phase 1: Backend foundation
- Phase 2: Shared core extraction
- Phase 3: Profile and jobs API
- Phase 4: Task-driven scoring and cover-letter generation in the API
- Phase 5: Frontend shell with real API wiring
- Phase 6: Browser AI workflow polish and completion
- Phase 7: Internal workspace management pivot
- Phase 8 core hardening slice

Important current reality:
- the CLI is still the most complete workflow
- the FastAPI backend is real and connected to Neon
- the Bun frontend is real and connected to the backend
- the database is now the source of truth for the web product path
- the browser product now uses the database and internal UI as its primary tracker and letter surface
- first-pass staging deployment scaffolding now exists for Render + Vercel

## Architecture Overview

The repo is intentionally a single-repo setup.

Current layers:

### `src/jobfit_cli/`

This remains the working command-line product.

Responsibilities:
- `jobfit setup`
- `jobfit score`
- OpenAI scoring and cover-letter orchestration through shared core services
- local archive persistence
- Google Docs export
- Google Sheets logging
- Google OAuth token handling for the CLI workflow

### `src/jobfit_core/`

This is the shared AI/domain layer extracted in Phase 2.

Responsibilities:
- evaluation schema
- prompt building
- applicant profile extraction
- OpenAI scoring
- cover-letter generation
- score-job workflow orchestration

This package is the key bridge between the CLI and API paths.

### `src/jobfit_api/`

This is the backend for the fullstack app.

Responsibilities:
- FastAPI app setup
- auth verification scaffolding
- SQLAlchemy models
- Alembic migration integration
- database-backed profile and jobs CRUD
- background task records
- task-driven scoring and cover-letter generation
- worker-backed execution when Redis is configured
- task retry metadata and manual retry handling
- request-id based request logging
- local CORS handling for frontend development

### `frontend/`

This is the Bun + React frontend.

Responsibilities:
- landing page
- auth-aware routing
- onboarding
- dashboard
- jobs list
- letters library
- job detail
- profile editor
- frontend API client and generated types

### `alembic/` and DB infrastructure

Responsibilities:
- database schema migrations
- Neon schema evolution
- local migration execution

## Repository Layout

```text
src/jobfit_cli/
src/jobfit_core/
src/jobfit_api/
frontend/
alembic/
data/
scripts/
```

High-signal files:

- `src/jobfit_core/workflows.py`
- `src/jobfit_core/openai_service.py`
- `src/jobfit_api/main.py`
- `src/jobfit_api/models.py`
- `src/jobfit_api/services.py`
- `src/jobfit_api/task_processing.py`
- `src/jobfit_api/routes/profile.py`
- `src/jobfit_api/routes/jobs.py`
- `render.yaml`
- `Dockerfile.api`
- `Dockerfile.worker`
- `DEPLOYMENT.md`
- `frontend/src/app/router.tsx`
- `frontend/src/pages/landing-page.tsx`
- `frontend/src/pages/onboarding-page.tsx`
- `frontend/src/pages/profile-page.tsx`
- `frontend/src/pages/job-detail-page.tsx`

## Phase 1: Backend Foundation

### Goal

Create the minimum real backend foundation for a SaaS transition:
- FastAPI
- DB config
- auth config
- migrations
- async scaffolding

### Implemented

- FastAPI app factory in `src/jobfit_api/main.py`
- root route `/`
- health route `/api/v1/health`
- auth identity route `/api/v1/auth/me`
- API settings loader in `src/jobfit_api/settings.py`
- SQLAlchemy engine/session management in `src/jobfit_api/database.py`
- initial DB models in `src/jobfit_api/models.py`
- Redis and Dramatiq scaffolding in `src/jobfit_api/queue.py`
- Alembic setup and first schema migration
- Docker Compose for local Postgres + Redis

### Important fixes completed in Phase 1

- Neon-style Postgres URLs are normalized to `postgresql+psycopg://...`
- Alembic reads the configured DB URL instead of silently defaulting to SQLite
- PostgreSQL enum migration bugs were fixed

### Verified

- Neon Postgres connection works
- Alembic migration runs against Postgres
- API boots locally
- `/` works
- `/api/v1/health` returns database `ok`

## Phase 2: Shared Core Extraction

### Goal

Move AI/domain logic out of the CLI so both CLI and API can use the same behavior.

### Implemented

- `src/jobfit_core/__init__.py`
- shared models in `src/jobfit_core/models.py`
- shared prompts in `src/jobfit_core/prompts.py`
- shared OpenAI logic in `src/jobfit_core/openai_service.py`
- reusable `JobApplicationService` in `src/jobfit_core/workflows.py`

### Important design result

The CLI no longer owns the scoring logic directly.

It still owns:
- stdin/stdout
- local file orchestration
- Docs/Sheets logging

But scoring and letter generation now live in shared code.

### Verified

- CLI still works
- shared workflow tests pass
- prompt and OpenAI tests pass

## Phase 3: Profile And Jobs API

### Goal

Create the first real database-backed product workflows:
- profile CRUD
- versioned resume/context storage
- jobs CRUD
- status history
- task lookup

### Implemented

In `src/jobfit_api/services.py`:
- internal user creation from auth context
- profile create/read/update
- resume version history
- context version history
- jobs create/read/update
- job status history
- task ownership lookup

Routes implemented:
- `GET /api/v1/profile`
- `POST /api/v1/profile`
- `PATCH /api/v1/profile`
- `GET /api/v1/jobs`
- `POST /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `PATCH /api/v1/jobs/{job_id}`
- `PATCH /api/v1/jobs/{job_id}/status`
- `GET /api/v1/tasks/{task_id}`

### Profile model behavior

Each user has one profile.

That profile stores versioned snapshots of:
- resume
- honest context

These versioned records are important because future evaluations and letters need to point back to the exact profile state used at that moment.

### Verified

- CRUD tests for profile and jobs pass
- status history behavior works
- task lookup works

## Phase 4: Task-Driven Scoring And Cover Letters

### Goal

Make the API able to trigger scoring and cover-letter generation through background-task records.

### Implemented

In `src/jobfit_api/task_processing.py`:
- create background task records
- queue in-process FastAPI background work
- load the latest profile snapshot for a job
- call `jobfit_core` shared workflow
- persist `evaluations`
- persist `cover_letters`
- persist task results/failure status

Endpoints added:
- `POST /api/v1/jobs/{job_id}/score`
- `POST /api/v1/jobs/{job_id}/cover-letter/regenerate`

Job detail responses now include:
- `latest_evaluation`
- `latest_cover_letter`

### Current async design

This is now task-driven with a real worker path.

Current behavior:
- API request creates a task row
- if `REDIS_URL` is configured, the API enqueues a Dramatiq actor
- a separate worker process can execute the task and move it from `queued` to `running` to `completed` or `failed`
- if `REDIS_URL` is blank, local dev and tests still fall back to in-process execution

### Verified

- score task tests pass
- cover-letter regeneration tests pass
- evaluation and letter persistence works
- worker dispatch tests pass for both Redis and non-Redis modes

## Phase 5: Frontend Shell

### Goal

Create the first browser interface on top of the API.

### Implemented

Stack:
- Bun
- React
- Vite
- TanStack Router
- TanStack Query
- TanStack Form
- Clerk browser auth
- Tailwind

Pages implemented:
- landing
- dashboard
- onboarding
- jobs
- job detail
- profile
- integrations
- settings

### Browser/API integration

The browser is wired to the real API contract.

Important frontend infrastructure:
- OpenAPI export script in `scripts/export_openapi.py`
- generated schema in `frontend/openapi.json`
- generated TS client types in `frontend/src/lib/api/generated.ts`
- browser API client in `frontend/src/lib/api/client.ts`
- hooks in `frontend/src/lib/api/hooks.ts`

### Current UX state

The frontend is real, but still early.

It is no longer just a static shell:
- profile writes to the API
- jobs write to the API
- job detail reads latest evaluation/letter data

But it still needs polish, especially around:
- richer loading states
- better error UX
- better production-grade onboarding flow

### Verified

- `bun test`
- `bun run build`

## Phase 6: Browser AI Workflow Completion

### Goal

Make the browser workflow feel like a real product surface rather than just a thin API demo.

### Implemented

- richer job list rows with latest score and latest workflow state
- richer dashboard metrics including scored roles, roles needing first score, and active AI tasks
- dashboard spotlight for the best current fit
- dashboard workflow-watch panel for active or failed task states
- improved suggested actions driven by scoring/task state rather than only manual status
- improved job detail page with:
  - task persistence across refresh/navigation when a task is still running
  - clearer task state presentation
  - better evaluation layout
  - better cover-letter preview
  - copy-to-clipboard for the latest cover letter
- API responses now surface latest evaluation and latest task on job list rows

### Important Phase 6 result

The browser now supports a full end-to-end AI workflow:

- create a job
- open detail
- run score
- watch task progress
- see evaluation refresh
- see letter refresh
- regenerate the letter again later

This is enough to treat Phase 6 as implemented.

### Remaining non-Phase-6 polish

The following still exists, but belongs more to future product hardening than to unfinished Phase 6:

- worker-process execution instead of in-process FastAPI background tasks
- further visual refinement and performance optimization

## New Work Added On 2026-03-31

This is the most recent set of changes and should be especially important in the next thread.

### 1. Profile uploads are now supported

Both profile inputs now support:
- direct text editing
- file upload

Supported upload formats:
- `.pdf`
- `.docx`
- `.txt`
- `.md`
- `.markdown`
- `.rst`
- `.json`
- `.csv`
- `.yaml`
- `.yml`

Current implementation details:
- uploads are sent from the frontend as base64 inside JSON
- the backend extracts readable text
- the extracted text becomes the profile content used for scoring
- the backend also stores file metadata in the DB
- the backend stores the raw uploaded file bytes in the DB

Backend pieces:
- `src/jobfit_api/documents.py`
- `src/jobfit_api/routes/profile.py`
- `src/jobfit_api/services.py`
- `src/jobfit_api/models.py`
- `alembic/versions/20260331_0002_profile_uploads.py`

Frontend pieces:
- `frontend/src/pages/onboarding-page.tsx`
- `frontend/src/pages/profile-page.tsx`
- `frontend/src/components/profile-document-field.tsx`
- `frontend/src/lib/uploads.ts`

### 2. Landing page signed-in state was fixed

There was a bug/UX failure where the signed-in landing state could look black and empty.

This was fixed by:
- replacing the signed-in CTA button variant
- improving the signed-in hero-side card
- adding a clearer profile-aware route target:
  - dashboard if profile exists
  - onboarding if profile does not exist

Files:
- `frontend/src/pages/landing-page.tsx`
- `frontend/src/components/ui.tsx`

### 3. Local API transport and CORS/dev setup were improved

Implemented:
- Vite dev proxy for `/api`
- default relative API base URL
- broader localhost CORS regex support in FastAPI

Files:
- `frontend/vite.config.ts`
- `frontend/src/lib/config.ts`
- `src/jobfit_api/main.py`
- `src/jobfit_api/settings.py`

## Phase 7: Internal Workspace Pivot

### Goal

Stop treating Google Docs and Google Sheets as the browser product surface and move that management flow fully inside the app.

### Implemented

Backend:
- internal cover-letter library route in `src/jobfit_api/routes/letters.py`
- jobs and task APIs now treat the database as the main tracker surface

Frontend:
- jobs page as the internal tracker
- `/app/letters` as the internal cover-letter library
- job detail focused on score, status, latest task, and latest letter inside the workspace

### Important Phase 7 result

The browser app now supports this flow:

- create and manage roles directly in the app
- score them and store the results in Postgres
- keep letters inside the app
- manage status and task state without leaving the product

The CLI is still valuable, but the browser product is now internal-workspace-first.

## Phase 8: Core Hardening Slice

### Goal

Make the task system safer for real use: worker execution, retry/backoff metadata, manual recovery, stronger auth validation, and better observability.

### Implemented

Backend:
- Redis + Dramatiq dispatch is now the real execution path when `REDIS_URL` is configured
- in-process FastAPI background tasks remain only as the local-dev fallback
- `background_tasks` records now include:
  - `attempt_count`
  - `max_attempts`
  - `last_attempt_at`
  - `next_retry_at`
- failed score and cover-letter tasks can be retried via `POST /api/v1/tasks/{task_id}/retry`
- worker retries now use explicit delayed requeue scheduling instead of relying on opaque actor retries
- request logging now adds `X-Request-ID` and logs request completion/failure with a request id
- app startup now validates required Clerk config when auth is enabled
- browser-only Google backend runtime code was removed from the API layer

Frontend:
- job detail now shows retry-oriented task metadata
- failed tasks can be retried directly from the workflow card
- active task polling understands queued/running/completed/failed plus retry timing

Deployment scaffolding:
- API container entrypoint in `scripts/start_api.sh`
- worker entrypoint in `scripts/start_worker.sh`
- migration entrypoint in `scripts/run_migrations.sh`
- backend Dockerfiles in `Dockerfile.api` and `Dockerfile.worker`
- Render blueprint in `render.yaml`
- Vercel SPA routing config in `frontend/vercel.json`
- deployment runbook in `DEPLOYMENT.md`

## Current Database State

The schema now includes:

- `users`
- `profiles`
- `resume_versions`
- `context_versions`
- `jobs`
- `evaluations`
- `cover_letters`
- `application_status_events`
- `background_tasks`

Plus the new upload-support columns on:
- `resume_versions`
- `context_versions`

New profile upload fields:
- `source_file_name`
- `source_file_mime_type`
- `source_file_size_bytes`
- `source_file_bytes`

New task reliability fields:
- `attempt_count`
- `max_attempts`
- `last_attempt_at`
- `next_retry_at`

## Migrations

Current migration history:
- `20260328_0001_backend_foundation`
- `20260331_0002_profile_uploads`
- `20260403_0003_phase8_hardening`

When working in a new thread, assume the DB must be migrated to head before testing upload features:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
.venv/bin/python -m alembic upgrade head
```

## How To Run Locally

### Backend

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
jobfit-api
```

### Frontend

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun run dev
```

### Important frontend env value

In `frontend/.env`, local development should use:

```env
VITE_API_BASE_URL=/api/v1
```

That lets Vite proxy API traffic instead of causing the old local CORS problem.

## How To Test Locally

### Full Python test suite

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
python -m unittest discover -s tests
```

### Frontend tests

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun test
```

### Frontend build

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun run build
```

### Manual backend smoke checks

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/api/v1/health
```

### Manual upload test

1. Start backend and frontend.
2. Sign in.
3. Open onboarding or profile.
4. Upload a resume PDF/DOCX/TXT.
5. Save.
6. Confirm:
   - extracted text appears in the text area
   - the latest saved file name appears in the UI
   - future score tasks still use the updated profile text

## Known Limitations

These are important for the next thread.

### Worker mode depends on Redis

If `REDIS_URL` is blank, the API still falls back to in-process execution for local development.

For production-shaped task behavior, Redis and the Dramatiq worker must both be running.

### PDF extraction is best-effort

The current PDF extraction is intentionally lightweight and local.

It works best for text-based PDFs.

It is not a full OCR or enterprise-grade PDF parser.

### Frontend polish is still needed

The browser app is functional, but still early in product quality.

The biggest gaps are:
- more refined dashboard UX
- stronger bundle/performance work
- more frontend test coverage
- more complete onboarding flow

## Recommended Next Priorities

If continuing implementation in a new thread, the safest high-value order is:

1. Keep hardening task operations
   - richer task telemetry
   - production monitoring and alerting
   - clearer worker failure surfaces

2. Tighten frontend/API contract and testing
   - more frontend tests
   - route-level task-flow tests
   - better auth-aware manual test guidance

3. Stand up real staging
   - provision Render API + worker
   - provision Vercel frontend
   - connect Neon and Redis
   - run migrations and smoke tests

## What To Remember In The Next Thread

- This is one repo, not separate frontend/backend repos.
- The CLI still matters and should not be broken casually.
- `jobfit_core` is the shared source of truth for scoring logic.
- The browser app is real, but not yet the production workflow.
- The backend is already wired to Neon.
- The frontend uses Bun, not npm or pnpm.
- The latest work added profile file-upload support and fixed the signed-in landing state.
- The browser product is internal-workspace-first now; remaining Google behavior mostly lives in the CLI only.
