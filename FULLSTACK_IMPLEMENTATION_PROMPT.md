# Applyflow Fullstack Implementation Prompt

We need to implement this fullstack application step by step because it includes a lot of moving pieces: frontend, backend API, database, async jobs, auth, integrations, and deployment.

Treat this as a phased implementation project, not a one-shot rewrite.

## Goal

Build `applyflow` as a public SaaS for individual job seekers.

The product should let a user:
- create an account
- save and manage their resume and honest context
- paste job descriptions
- get an honest AI fit score from `0-100`
- generate a concise cover letter
- track application status
- optionally export cover letters to Google Docs
- optionally sync jobs to Google Sheets

## Current State

This repo already contains the domain logic in Python for:
- job fit evaluation
- cover letter generation
- Google Docs creation
- Google Sheets sync
- local artifact storage
- CLI-based workflow

Important:
- keep this repo as the backend/core starting point
- do not throw away the Python logic
- preserve the current CLI while we transition to a web product
- if a `frontend/` directory exists, use and extend it instead of recreating the frontend from scratch
- if a `frontend/` directory does not exist yet, build the backend foundation first and add the frontend in a later phase

## Product Defaults

Use these defaults unless there is a strong technical reason to change them:
- audience: individual job seekers
- v1 scope: core apply cockpit
- auth: yes
- billing: no, not in v1
- data source of truth: application database
- Google Docs and Sheets: optional integrations, not primary storage
- async UX: polling in v1, not websockets
- cloud posture: managed-first, AWS optional later
- deployment target for v1: fast managed services, with an architecture that can later move to AWS

## Recommended Stack

Frontend:
- React 19
- TypeScript
- Vite
- TanStack Router
- TanStack Query
- TanStack Form
- TanStack Table
- Tailwind CSS
- shadcn/ui
- Zod

Backend:
- FastAPI
- Pydantic v2
- SQLAlchemy 2
- Alembic
- PostgreSQL
- Redis
- Dramatiq for background jobs

Auth:
- Clerk on the frontend
- Clerk JWT verification in FastAPI

Infra for v1:
- Vercel for frontend
- Render or Railway for API and worker
- Neon for Postgres
- Upstash for Redis

## Architecture Direction

Keep the current Python repo as the core engine and evolve it into:
- reusable domain services
- a FastAPI backend
- a background worker
- a persistent database-backed application

The CLI should become a thin client over the same core services.

The database must replace local files as the primary runtime source of truth.

## Core Entities

Design the backend and database around these entities:
- users
- profiles
- resume_versions
- context_versions
- jobs
- evaluations
- cover_letters
- application_status_events
- google_connections
- google_documents
- google_sheet_syncs
- background_tasks

Important model rule:
- each scoring run should use a snapshot of the user profile at that time so past results remain reproducible

## Required User Flows

V1 must support these flows:
- sign up and sign in
- onboarding
- create or update profile
- paste a job description
- score the job
- generate a cover letter
- view strengths, gaps, verdict, and feedback
- view and update application status
- connect Google account
- export cover letter to Google Docs
- optionally sync a job row to Google Sheets

## API Surface To Build

Create a versioned API, for example `/api/v1`.

Minimum endpoints:
- `GET /profile`
- `POST /profile`
- `PATCH /profile`
- `POST /jobs`
- `GET /jobs`
- `GET /jobs/{id}`
- `PATCH /jobs/{id}`
- `PATCH /jobs/{id}/status`
- `POST /jobs/{id}/score`
- `POST /jobs/{id}/cover-letter/regenerate`
- `GET /tasks/{id}`
- `POST /integrations/google/connect/start`
- `POST /integrations/google/connect/complete`
- `DELETE /integrations/google`
- `POST /jobs/{id}/export/google-doc`
- `POST /jobs/{id}/sync/google-sheet`

Async endpoints should return a task ID immediately.

## Frontend Scope

Use the existing `frontend/` app as the web client if it exists.

Pages to build in v1:
- landing page
- auth pages
- onboarding
- dashboard
- jobs list
- job detail
- profile
- integrations
- settings

Core UI requirements:
- table-based jobs list first
- filters for status, score, company, role, and date
- clear async task states
- strong loading and error handling
- a simple, polished, modern UI
- preserve any good existing frontend setup in `frontend/`

## Implementation Phases

### Phase 1: Backend foundation
- create FastAPI app structure
- add Postgres, SQLAlchemy, and Alembic
- add Redis and background job support
- add config and environment separation
- add auth verification
- define initial DB schema

Acceptance:
- backend runs locally
- migrations work
- auth can identify a user
- database connection is healthy

### Phase 2: Extract reusable core services
- move current scoring and cover-letter logic into shared services
- remove direct CLI-only coupling from business logic
- keep current prompts, model fallback, validation, and repair logic
- preserve current cover-letter shaping and one-page constraints

Acceptance:
- CLI still works
- service layer can be called from API code
- business logic no longer depends on local CLI I/O

### Phase 3: Profile and jobs domain
- implement profile CRUD
- implement job CRUD
- implement profile snapshot/version model
- implement application status model and history
- implement task tracking model

Acceptance:
- user can create profile
- user can create a job
- status updates persist
- snapshots are created for scoring runs

### Phase 4: Scoring and cover-letter async workflow
- add scoring task
- add cover-letter generation task
- persist results in DB
- expose task polling endpoints
- handle retries and failure states

Acceptance:
- a job can be scored from the API
- a cover letter is generated and saved
- frontend can poll task status
- failures are visible and recoverable

### Phase 5: Frontend application shell
- wire auth in the `frontend/` app
- build protected routes
- build onboarding
- build jobs list and job detail pages
- build profile editor
- integrate typed API client

Acceptance:
- a signed-in user can navigate the app
- the profile can be edited
- jobs list and job detail pages work end to end

### Phase 6: Frontend AI workflow
- trigger scoring from the job detail page
- display task progress
- render score, verdict, strengths, gaps, and feedback
- render cover-letter preview
- support cover-letter regeneration

Acceptance:
- user can run the full AI workflow from the browser
- progress and errors are clear
- results persist across refreshes

### Phase 7: Google integrations
- add per-user Google OAuth connection
- store encrypted Google tokens
- export cover letters to Google Docs
- sync jobs to Google Sheets
- keep these optional

Acceptance:
- app works without Google
- user can connect Google
- a cover letter can be exported to Docs
- a job can be synced to Sheets

### Phase 8: Hardening for public beta
- add rate limiting
- add audit logging
- add better observability
- add staging environment
- add structured error reporting
- add basic abuse protection
- add prompt/model version tracking

Acceptance:
- app is safe enough for public beta
- failures are observable
- important workflows are traceable

## Frontend Rules

Important rules for the `frontend/` directory:
- do not recreate the frontend from scratch if the foundation is already good
- inspect and preserve existing conventions
- prefer modern TanStack patterns
- use typed API contracts generated from the backend OpenAPI schema
- prioritize a clean, intentional UI over generic boilerplate
- make desktop and mobile both work well

## Backend Rules

Important rules for the backend transition:
- keep the CLI usable during the migration
- do not duplicate the scoring logic in multiple places
- the API and CLI must use the same core services
- use the database as the real source of truth
- local files should become import/debug artifacts, not production state

## Testing Requirements

At minimum, include:
- unit tests for prompt and domain logic
- API tests for auth and CRUD
- worker tests for async task behavior
- frontend tests for key pages and task polling
- end-to-end tests for signup, onboarding, job scoring, and Google export

## Non-Goals For V1

Do not build these in v1 unless explicitly requested later:
- billing
- browser extension
- automatic job scraping
- team collaboration
- coach workflows
- recruiter workflows
- websocket live updates
- advanced analytics
- AWS-first infrastructure
- autonomous multi-step application agents

## Working Style

Implement this project phase by phase.

For each phase:
1. inspect the existing code first
2. propose the smallest safe implementation slice
3. implement it fully
4. test it
5. summarize what changed
6. only then move to the next phase

Start with Phase 1.

Do not jump ahead to advanced features before the foundation is stable.
