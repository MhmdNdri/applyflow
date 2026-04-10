# Applyflow Next-Thread Handoff

Use this file as the starting context for the next implementation thread.

## Project Summary

`applyflow` is a single-repo project that currently contains:

- a working Python CLI for job-fit scoring and cover-letter generation, with legacy Google export/logging still present there
- a shared AI/domain layer in `src/jobfit_core/`
- a FastAPI backend in `src/jobfit_api/`
- a Bun + React frontend in `frontend/`
- a Neon Postgres database with Alembic migrations

This repo is not a prototype anymore. It already has real backend, DB, frontend, and CLI behavior.

## Important Current Status

Completed:
- Phase 1: Backend foundation
- Phase 2: Shared core extraction
- Phase 3: Profile and jobs API
- Phase 4: Task-driven scoring and cover-letter generation in the API
- Phase 5: Frontend shell with real API wiring
- Phase 6: Browser AI workflow
- Phase 7: Internal workspace management pivot
- Phase 8 core hardening slice: worker dispatch, retry metadata, manual retry, request IDs, and backend Google cleanup

## Most Recent Changes

The latest implemented changes are:

1. Profile uploads
- resume and honest context now support file upload in onboarding and profile pages
- supported formats include PDF, DOCX, TXT, and Markdown-style files
- backend extracts readable text and stores file metadata plus raw bytes in the DB

2. Signed-in landing fix
- the signed-in landing state no longer collapses into a black/empty-looking panel
- signed-in CTA now routes to onboarding if profile is missing, or dashboard if profile exists

3. Local frontend/API transport improvements
- Vite proxy is used for `/api`
- local frontend should use `VITE_API_BASE_URL=/api/v1`
- backend now allows localhost/127.0.0.1 origins more flexibly

4. Phase 6 browser workflow completion
- dashboard now shows scored roles, active AI tasks, best current fit, and workflow-watch cards
- jobs list now shows latest score and workflow state
- job detail now has a stronger task panel, better evaluation layout, cover-letter copy action, and task persistence across refreshes
- API job list/detail responses now include latest task summaries

5. Internal workspace pivot
- the browser product no longer depends on Google as its main management surface
- the jobs page is now positioned as the internal tracker or private spreadsheet
- a new internal letters library exists at `/app/letters`
- job detail now treats the latest score, status, and letter as internal workspace records
- the product-facing Google integrations page and Google job-detail actions were removed
- the backend now exposes `GET /api/v1/cover-letters`

6. Phase 8 hardening slice
- `REDIS_URL` now enables real Dramatiq worker execution instead of in-process task execution
- background tasks now track `attempt_count`, `max_attempts`, `last_attempt_at`, and `next_retry_at`
- failed score and cover-letter tasks can be retried through `POST /api/v1/tasks/{task_id}/retry`
- the job detail page now exposes retry UI for failed tasks
- backend request logging now emits request IDs and returns `X-Request-ID`
- backend-only Google runtime code and browser Google routes/schema were removed

7. Staging/deployment scaffolding
- backend Dockerfiles now exist for the API and worker
- startup and migration scripts now exist in `scripts/`
- a Render blueprint now exists in `render.yaml`
- the frontend now has `frontend/vercel.json` for SPA rewrites on Vercel
- the deployment runbook now exists in `DEPLOYMENT.md`

## Files To Read First In The Next Thread

Read these first before implementing anything:

- `FULLSTACK_IMPLEMENTATION_STATUS.md`
- `README.md`
- `src/jobfit_core/workflows.py`
- `src/jobfit_api/main.py`
- `src/jobfit_api/services.py`
- `src/jobfit_api/task_processing.py`
- `src/jobfit_api/routes/letters.py`
- `src/jobfit_api/routes/profile.py`
- `src/jobfit_api/routes/jobs.py`
- `DEPLOYMENT.md`
- `render.yaml`
- `Dockerfile.api`
- `Dockerfile.worker`
- `frontend/src/app/router.tsx`
- `frontend/src/pages/landing-page.tsx`
- `frontend/src/pages/onboarding-page.tsx`
- `frontend/src/pages/profile-page.tsx`
- `frontend/src/pages/job-detail-page.tsx`
- `frontend/src/pages/jobs-page.tsx`
- `frontend/src/pages/letters-page.tsx`

## Current Database Notes

Migration history currently includes:
- `20260328_0001_backend_foundation`
- `20260331_0002_profile_uploads`
- `20260403_0003_phase8_hardening`

Before testing profile upload behavior against Neon, run:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
.venv/bin/python -m alembic upgrade head
```

## How To Run The Project

Backend:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
jobfit-api
```

Frontend:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun run dev
```

Frontend env:

```env
VITE_API_BASE_URL=/api/v1
```

## How To Test

Python:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
python -m unittest discover -s tests
```

Frontend:

```bash
cd /Users/mhmd_ndri/Desktop/apply/frontend
bun test
bun run build
```

## Key Product Rules

- Keep this as one repo unless there is a very strong reason to split it later.
- Do not break the CLI while improving the web app.
- Treat `src/jobfit_core/` as the shared source of truth for AI behavior.
- The database is the source of truth for the web product path.
- The browser product is now internal-workspace-first, while legacy Google behavior still mostly lives in the CLI codepath.

## Recommended Next Step

The best next step is the rest of public-beta hardening:

- add deeper worker retry policies and operational monitoring
- tighten frontend test coverage around the internal tracker and internal letters workflow
- keep polishing the browser UX and bundle size
- decide whether the CLI’s legacy Google export path should stay as a legacy feature or be removed later
- after that, stand up the real staging environment using the new deployment scaffolding

After that, continue with broader public-beta hardening.
