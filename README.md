# Job Fit Evaluator CLI

Job Fit Evaluator is a Python CLI for running an honest AI-assisted job application workflow from your terminal.

It lets you keep one local resume and one long-term context file, paste any job description, score your fit from `0-100`, generate a tailored cover letter, archive the full run locally, create a Google Doc for the letter, and log the result into Google Sheets.

## What It Does

- scores a job description against your resume and context using the OpenAI Responses API
- returns a strict fit score with concise feedback
- generates a short, humanized cover letter
- keeps local archives of job descriptions, letters, and run metadata
- creates a Google Doc for each cover letter
- appends a clean tracking row to Google Sheets
- adds sheet formatting, score highlighting, and an application-status column

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
- less manual copy-paste between AI, Google Docs, and Sheets

## Project Structure

```text
src/jobfit_cli/
  app.py              Main setup and scoring workflow
  cli.py              CLI entrypoint
  config.py           Environment and path loading
  constants.py        Shared defaults and sheet schema constants
  docs.py             Google Docs and Drive integration
  google_auth.py      Google OAuth and service-account auth helpers
  models.py           Typed fit-evaluation schema
  openai_service.py   OpenAI scoring and cover-letter generation
  prompts.py          Prompt builders and applicant-profile extraction
  sheets.py           Google Sheets logging, migration, and formatting
  storage.py          Local file persistence helpers

data/
  profile/            Reusable resume and context
  jobs/               Raw pasted job descriptions
  letters/            Local cover-letter backups
  runs/               JSON run metadata
  google/             OAuth token storage
```

## Requirements

- Python `3.14+`
- an OpenAI API key
- a Google account with:
  - Google Sheets API enabled
  - Google Docs API enabled
  - Google Drive API enabled
- a Google OAuth desktop client JSON for personal Gmail usage

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
GOOGLE_SHEET_ID=your_google_sheet_id
GOOGLE_OAUTH_CLIENT_FILE=credentials/google-oauth-client.json
GOOGLE_OAUTH_TOKEN_FILE=data/google/oauth-token.json
GOOGLE_DRIVE_FOLDER_ID=your_google_drive_folder_id
```

Optional fallback for Google Workspace or bot-style setups:

```env
GOOGLE_SERVICE_ACCOUNT_FILE=credentials/google-service-account.json
```

### Recommended Google Setup For Personal Gmail

For a personal Google Drive account, use OAuth.

1. Create or select a Google Cloud project.
2. Enable:
   - Google Sheets API
   - Google Docs API
   - Google Drive API
3. Create an OAuth client of type `Desktop app`.
4. Download the JSON and place it in:
   - `credentials/google-oauth-client.json`
5. Create a folder in Google Drive for generated cover letters.
6. Copy that folder ID into `GOOGLE_DRIVE_FOLDER_ID`.
7. If the OAuth app is still in testing mode, add your Gmail as a test user.

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

Before pushing this project publicly:

1. initialize Git
2. confirm only safe files are tracked
3. make the first commit
4. push to GitHub

Suggested commands:

```bash
cd /path/to/project
git init
git add .
git status
```

Before committing, verify that these are **not** staged:

- `.env`
- `credentials/`
- `data/`
- `.venv/`

Then commit:

```bash
git commit -m "Initial commit"
```

And connect your GitHub remote:

```bash
git remote add origin <your-github-repo-url>
git branch -M main
git push -u origin main
```

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

## Test Commands

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
.venv/bin/python -m unittest discover -s tests
```

## License

No license file has been added yet. Add one before publishing publicly if you want reuse terms to be explicit.
