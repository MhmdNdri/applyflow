# Job Fit Evaluator CLI

## Complete Project Report And Documentation

Last updated: 2026-03-27

## 1. Project Purpose

This project was built to support a real job-application workflow with as little repeated manual work as possible.

The original idea was:

- store one master resume locally
- store one honest long-term context file locally
- paste a job description into the CLI
- let AI evaluate actual fit from `0` to `100`
- return concise, honest feedback
- store the result locally
- log the important summary into Google Sheets

The workflow was later extended to also:

- generate a concise, humanized cover letter for each job
- save the cover letter locally
- create a Google Doc for the cover letter
- store only the Google Doc link in the spreadsheet
- improve the spreadsheet visually
- add an application-status tracking column

This project is intentionally strict. It is meant to help with honest decision-making, not optimistic fluff.

## 2. Final Outcome

The final tool is a standalone Python CLI named `jobfit`.

It currently supports two commands:

- `jobfit setup`
- `jobfit score`

### `jobfit setup`

This command:

- loads `.env`
- creates local profile template files if they do not exist
- validates OpenAI access
- validates Google Docs access
- validates Google Sheets access
- upgrades the first worksheet schema if needed
- applies worksheet formatting and dropdown/status styling
- stores a reusable Google OAuth token when OAuth is configured

### `jobfit score`

This command:

- reads the current resume and context from local files
- accepts a pasted job description
- scores the job using OpenAI
- generates a tailored cover letter
- saves the raw job description locally
- saves the cover letter locally
- saves a JSON run record locally
- creates a Google Doc for the cover letter
- appends a summary row to Google Sheets

## 3. Core Product Decisions From The Thread

Several important product and technical decisions were made during implementation.

### Strict fit evaluation

The score is designed to be honest and evidence-based.

The prompt explicitly tells the model to:

- punish missing must-have requirements heavily
- reward proven evidence from the resume and context
- avoid inventing unknown metadata
- return exactly 3 strengths and 3 gaps
- keep feedback concise

### Separate resume and honest context

The project stores two different profile inputs:

- `data/profile/resume.md`
- `data/profile/context.md`

This was important because the workflow needed both:

- a polished professional record
- a more candid internal context across the whole job search

### Google Sheets is a tracker, not the full archive

The spreadsheet stores only summaries and links.

The full raw materials stay local:

- full pasted job descriptions
- generated cover letters
- detailed run metadata

### Cover letters should be linked, not pasted into Sheets

Instead of stuffing long cover-letter text into a spreadsheet row, the final design creates a Google Doc and stores only a clickable link in the sheet.

### Personal Gmail requires OAuth

A key implementation lesson from this thread:

- service-account auth worked for some Google operations
- but it failed for creating owned Docs in a personal Gmail Drive setup
- Google returned Drive quota and ownership errors

Because of that, the project was redesigned to support Google OAuth user credentials and to prefer OAuth for personal Gmail usage.

## 4. Architecture Overview

The project is organized as a small CLI package under `src/jobfit_cli/`.

Main modules:

- `src/jobfit_cli/cli.py`
  - command-line entrypoint
- `src/jobfit_cli/app.py`
  - orchestration for `setup` and `score`
- `src/jobfit_cli/openai_service.py`
  - OpenAI Responses API calls, structured evaluation parsing, model fallback, repair path
- `src/jobfit_cli/prompts.py`
  - evaluation and cover-letter prompt construction
- `src/jobfit_cli/models.py`
  - typed evaluation schema
- `src/jobfit_cli/sheets.py`
  - Google Sheets schema migration, logging, formatting, validation, and status rules
- `src/jobfit_cli/docs.py`
  - Google Docs and Drive document creation
- `src/jobfit_cli/google_auth.py`
  - shared Google auth layer for OAuth and service-account fallback
- `src/jobfit_cli/config.py`
  - environment loading and path resolution
- `src/jobfit_cli/storage.py`
  - local persistence helpers
- `src/jobfit_cli/constants.py`
  - shared defaults, templates, and sheet constants

## 5. Runtime Workflow

### 5.1 Setup Flow

When `jobfit setup` runs:

1. The app resolves the project root and loads `.env`.
2. It ensures all required local data directories exist.
3. It creates starter profile templates if needed.
4. It validates OpenAI access.
5. It validates Google auth and API access.
6. It validates Google Docs creation.
7. It validates Google Sheets access and upgrades the sheet schema if required.
8. It applies the sheet styling and validation rules.

If OAuth is configured and the token does not yet exist:

- a browser login flow opens
- the user signs in with their Gmail
- the local token is saved for later runs

### 5.2 Score Flow

When `jobfit score` runs:

1. The app loads `resume.md` and `context.md`.
2. It reads the pasted job description.
3. It warns if the description is very sparse.
4. It sends the evaluation prompt to OpenAI.
5. It validates or repairs the structured evaluation result.
6. It extracts the applicant name, email, and phone from the resume.
7. It sends a second prompt to OpenAI to generate the cover letter.
8. It writes local artifacts:
   - archived job description
   - cover-letter backup
   - JSON run record
9. It creates a Google Doc for the cover letter.
10. It appends a row to Google Sheets.

If the Google Doc or Google Sheets step fails after scoring:

- local artifacts are still kept
- the tool returns a partial-failure message
- the run record captures the failure details

## 6. AI Behavior

### 6.1 Evaluation Output

The evaluation schema includes:

- `score`
- `verdict`
- `company`
- `role_title`
- `location`
- `source_url`
- `top_strengths`
- `critical_gaps`
- `feedback`

The output is validated with a strict JSON schema.

The app also includes recovery logic for model output problems:

- trims extra strengths/gaps down to exactly 3
- trims feedback to 4 sentences if needed
- makes one repair call if output is still invalid

### 6.2 Model Fallback

The default requested model is:

- `gpt-5.4-mini`

If the current API project does not have access to it, the app automatically falls back to:

- `gpt-4o-mini`

The run metadata and CLI output record which model actually ran.

### 6.3 Cover Letter Rules

The cover-letter prompt currently enforces:

- warm-professional tone
- concise structure
- exactly 3 short body paragraphs
- no fake claims
- direct tailoring to the role and company when known
- explicit header details
- proper sign-off

The cover letter now tries to include:

- applicant full name
- applicant email
- applicant phone
- human-readable application date
- greeting
- 3 body paragraphs
- closing such as `Best regards,` or `Cheers,`
- applicant full name at the end

## 7. Local Data Layout

The project uses `data/` as its local working store.

### Profile

- `data/profile/resume.md`
- `data/profile/context.md`

### Google auth

- `data/google/oauth-token.json`

### Job archives

- `data/jobs/`

Each job description is archived as a Markdown file.

### Cover-letter backups

- `data/letters/`

Each generated cover letter is saved locally as Markdown.

### Run records

- `data/runs/`

Each run record is stored as JSON and includes:

- run ID
- date
- timestamp
- model used
- profile hash
- application status
- archive paths
- cover-letter text
- Google Doc URL if available
- evaluation payload
- doc logging status
- sheet logging status

## 8. Google Integration Design

### 8.1 Supported auth modes

The app supports two Google auth modes:

- OAuth user credentials
- service account credentials

OAuth is preferred when `GOOGLE_OAUTH_CLIENT_FILE` is present.

### 8.2 Why OAuth was added

During implementation, service-account auth caused a real problem for personal Gmail Drive usage.

Observed issue:

- Google Docs creation failed with Drive storage quota / ownership errors

Reason:

- the service account was effectively trying to create and own the generated Docs
- this is a poor fit for a personal Gmail Drive setup

Final solution:

- use OAuth so the files are created under the user’s own Google account

### 8.3 Required Google APIs

The workflow requires:

- Google Sheets API
- Google Docs API
- Google Drive API

### 8.4 OAuth consent screen note

Because the OAuth app may remain in testing mode, the Gmail account used for login may need to be explicitly added as a test user in Google Cloud.

This happened during the build and is now part of the known setup process.

## 9. Spreadsheet Design

The first worksheet in the spreadsheet is used.

Current headers:

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

### Formatting behavior

`jobfit setup` applies:

- frozen header row
- styled header colors
- alternating row banding
- adjusted column widths
- centered score cells
- score-based conditional colors
- application status validation and colors

### Application status

Status options are:

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

Default status for new rows:

- `waiting`

Important note:

The current implementation supports a single current status per row with validation and colors.

It is not true multi-select status history inside one cell.

That was the closest safe implementation for the current Sheets API path while preserving a clean tracker.

### Sheet migration behavior

The app can migrate:

- the original legacy schema with `timestamp`
- the intermediate schema without `application_status`

During migration:

- `timestamp` is normalized to day-only `YYYY-MM-DD`
- `application_status` is inserted with the default `waiting`
- old rows are preserved

## 10. Cover Letter Document Design

For each scored job:

- the cover letter is saved locally
- a Google Doc is created
- the sheet stores only a hyperlink formula to the doc

The Google Doc title currently includes:

- human-readable application date
- applicant name
- role title
- company name

The goal is to make each generated document easier to recognize from Drive without opening it.

## 11. Configuration

Main environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `GOOGLE_SHEET_ID`
- `GOOGLE_OAUTH_CLIENT_FILE`
- `GOOGLE_OAUTH_TOKEN_FILE`
- `GOOGLE_DRIVE_FOLDER_ID`
- `GOOGLE_SERVICE_ACCOUNT_FILE`

Recommended personal Gmail configuration:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-mini
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_OAUTH_CLIENT_FILE=credentials/google-oauth-client.json
GOOGLE_OAUTH_TOKEN_FILE=data/google/oauth-token.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

Service-account auth remains optional for other environments, but OAuth is the recommended path for a personal Gmail Drive.

## 12. First-Time Setup Guide

### 12.1 Python environment

```bash
cd /Users/mhmd_ndri/Desktop/apply
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 12.2 OpenAI setup

- create an OpenAI API key
- place it in `.env`

### 12.3 Google setup

1. Create or select the Google Cloud project.
2. Enable:
   - Google Sheets API
   - Google Docs API
   - Google Drive API
3. Create an OAuth client of type `Desktop app`.
4. Download the OAuth JSON.
5. Put it in `credentials/google-oauth-client.json`.
6. Set `GOOGLE_OAUTH_CLIENT_FILE` in `.env`.
7. Create a Drive folder for generated cover letters.
8. Copy the folder ID into `GOOGLE_DRIVE_FOLDER_ID`.
9. Make sure the OAuth consent screen can be used by your Gmail:
   - if the app is in testing mode, add your Gmail as a test user

### 12.4 Sheet setup

- create the Google Sheet
- copy the sheet ID from the URL
- set `GOOGLE_SHEET_ID`

### 12.5 Run setup

```bash
jobfit setup
```

On first OAuth use:

- the browser login opens
- you approve access
- the token file is generated automatically

### 12.6 Fill profile files

Add content to:

- `data/profile/resume.md`
- `data/profile/context.md`

## 13. Daily Usage

The normal daily flow is:

```bash
cd /Users/mhmd_ndri/Desktop/apply
source .venv/bin/activate
jobfit score
```

Then:

- paste the full job description
- press `Ctrl-D`

You can also pipe clipboard text:

```bash
pbpaste | jobfit score
```

Expected output:

- numeric score
- verdict
- strengths
- gaps
- concise feedback
- local cover-letter path
- Google Doc link if created
- archived job path
- run record path

## 14. Testing

The project includes unit and integration-style tests for:

- prompt assembly
- evaluation schema validation
- OpenAI fallback behavior
- evaluation repair behavior
- setup flow
- score flow
- sheet migration logic
- sheet formatting helpers

Current passing test commands:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
.venv/bin/python -m unittest discover -s tests
```

## 15. Problems Encountered During Development

This section captures the important real issues discovered during the thread.

### 15.1 OpenAI validation token minimum

Issue:

- OpenAI rejected too-small `max_output_tokens` during validation

Fix:

- validation now uses `max_output_tokens=16`

### 15.2 Model access mismatch

Issue:

- the account initially lacked access to the requested GPT-5 mini variant

Fix:

- fallback support was added so the tool can retry with `gpt-4o-mini`

### 15.3 Structured-output schema incompatibility

Issue:

- OpenAI rejected the original schema because nullable fields still had to be listed in `required`

Fix:

- the schema was rewritten explicitly so every field is included in `required`

### 15.4 Near-valid JSON from the model

Issue:

- model outputs could still violate exact constraints such as too many strengths or too-long feedback

Fix:

- added sanitization and one repair call

### 15.5 Google Docs and Drive with service account on personal Gmail

Issue:

- document creation failed due to quota/ownership constraints

Fix:

- moved to OAuth-based Google user auth for personal Gmail usage

### 15.6 OAuth access blocked

Issue:

- Google denied access because the OAuth app was still in testing and the Gmail account was not an approved tester

Fix:

- add the Gmail account as a test user in Google Cloud

## 16. Known Limitations

- The application-status column is single-select, not real multi-select.
- Contact extraction from the resume uses simple heuristics. If the resume format is unusual, the parsed name or phone may be imperfect.
- The cover-letter structure depends on the model following instructions closely, although the prompt is now more explicit.
- The first worksheet is assumed to be the tracking sheet.
- The current CLI only supports `setup` and `score`; there is no dedicated command yet for updating a row status after applying.
- Packaging refresh may fail in a fully offline environment if `pip install -e .` tries to rebuild without cached build tools.

## 17. Good Next Improvements

Good future improvements would be:

- add a `jobfit status` command to update application status from the terminal
- add better resume parsing for name, phone, and email
- add optional custom cover-letter styles
- add company/role deduplication logic in the spreadsheet
- add a retry command for doc or sheet logging from saved run JSON
- add support for editing or re-generating a cover letter from a saved run
- add a richer sheet dashboard or summary tab

## 18. Executive Summary

This project successfully evolved from a simple scoring script into a small end-to-end application workflow tool.

It now:

- stores reusable candidate context locally
- scores job fit honestly
- writes tailored cover letters
- archives all important artifacts locally
- logs results into a visually improved Google Sheet
- creates shareable Google Docs for each cover letter
- supports personal Gmail via OAuth

The implementation reflects the practical lessons discovered during real setup and testing, especially around OpenAI structured outputs and Google auth for personal Drive usage.
