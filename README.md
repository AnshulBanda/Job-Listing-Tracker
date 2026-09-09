# JobsApplier (Placement Tracker)

A GenAI system that monitors job/internship alert emails, matches opportunities against my resume(s) and stated preferences, and surfaces everything in Notion with a fit score, reasoning, and apply link — plus a calendar of tests, interviews, and deadlines.

Built during campus placement season as a way to stop manually tracking every job alert across nine planned sources plus company alerts, while also serving as a portfolio project.

## Documentation

- [Project blueprint](docs/blueprint.md): architecture, scope, and database schemas.
- [Current checkpoint](docs/checkpoint.md): verified progress, decisions, limitations, and next steps.

## Architecture

```text
[Resume folder] -> [0. Profile Store] ----------------------+
                                                          |
[Gmail inbox] -> [1. Ingestion] -> [2. Extraction] -> [3. Matching]
                                                          |
                                                          v
                                                  [4. Notion sync]
                                                   /            \
                                         Job Opportunities   Placement Calendar
```

## Status

* [x] **Component 0 — Resume/Profile Store**: parses resume PDFs into structured JSON via a local LLM, with hash-based change detection so unchanged resumes are never re-parsed. Supports multiple resume versions (SWE, Data Science, and future GenAI/Cloud versions).
* [x] **Notion database setup**: both schemas and their one-way relation verified; sequential reruns reuse existing databases. Schedule calendar view configured manually.
* [x] **PES Gmail ingestion milestone**: read-only OAuth, paginated downloads, body decoding, local JSON records, retries, and rerun skipping verified.
* [ ] **Component 1 — remaining Gmail sources**: other fixed sources, company allowlist, and ingestion hardening.
* [ ] **Component 2 — Email extraction**
* [ ] **Component 3 — Matching**
* [ ] **Component 4 — Notion sync**
* [ ] **Component 5 — Orchestration**

## Component 0: Resume/Profile Store

Watches a `resumes/` folder and turns each resume PDF into structured profile data — contact info, skills (by category), experience, projects, education, certifications — plus an inferred `target_role_focus` per resume, so a later matching step can pick the best-fit resume version per job posting.

### Design Decisions

* **Local LLM via Ollama** (`llama3.1:8b`), not a hosted API — no cost, no rate limits, fully offline, consistent with other projects in my portfolio (Prob.lm, NutriChat).
* **Hash-based change detection** — each resume's SHA-256 hash is stored alongside its parsed profile. Re-parsing only happens when a file is new or its content actually changed, not on every run.
* **Pydantic schema** (`schema.py`) as the single source of truth for what "structured resume data" means — both the LLM's output and the on-disk state (`profile_state.json`) are validated against it.

### Files

* `schema.py` — Pydantic models (`ResumeProfile`, `ProfileState`, `Preferences`, etc.)
* `parser.py` — PDF text extraction (`pdfplumber`) + LLM structuring (Ollama)
* `store.py` — `sync_resumes()`: scans `resumes/`, re-parses changed files, writes `profile_state.json`

## Tech Stack

* **Language:** Python
* **Local LLM:** Ollama (`llama3.1:8b`)
* **PDF parsing:** pdfplumber
* **Schema validation:** Pydantic
* **Notion setup:** `notion-client` + `python-dotenv`
* **Folder watching:** `watchdog`
* **Email:** Gmail API + Google OAuth client libraries
* **HTML parsing:** Beautiful Soup
* **Planned:** structured email extraction, matching, and automated Notion entry synchronization

## Setup

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
ollama pull llama3.1:8b
```

Copy resume PDF(s) into `component0_profile_store/resumes/`, and copy `component0_profile_store/preferences.example.json` to `preferences.json`, filling in your own target roles / locations / etc.

### Run the Sync

```powershell
cd component0_profile_store
py -c "from store import sync_resumes; sync_resumes()"
```

## Notion Database Setup

Create a parent page in Notion, connect the JobsApplier integration, and set these variables in a project-root `.env` file (gitignored):

```dotenv
NOTION_TOKEN=<your integration token>
NOTION_PARENT_PAGE_ID=<your parent page ID>
```

Run from the project root:

```powershell
.\venv\Scripts\python.exe .\component_notion\setup_databases.py
```

The script creates Job Opportunities and Placement Calendar when missing, or reuses direct child databases with the same titles. It uses `initial_data_source.properties` and links calendar events to the Job Opportunities data source. Reuse does not migrate or repair existing schemas, and renamed databases or concurrent runs can cause duplicates.

Add a Calendar view named Schedule to Placement Calendar, using its Date property. Date supports optional times; separate rows allow multiple events on one day. The script creates the schemas, not the view or automated entry synchronization.

## Component 1: PES Gmail Ingestion

Enable Gmail API in a Google Cloud project. Configure an External OAuth app for personal Gmail use, add the intended mailbox as a test user, add the `gmail.readonly` scope, and create a Desktop app OAuth client. The project owner and authorized mailbox can be different accounts.

Save the downloaded client JSON as `component1_gmail/credentials.json`. Dependencies are included in `requirements.txt`. Run from the project root:

```powershell
.\venv\Scripts\python.exe .\component1_gmail\auth.py
.\venv\Scripts\python.exe .\component1_gmail\ingest.py
```

Authorize the mailbox receiving placement alerts. `auth.py` stores authorization in `component1_gmail/token.json` and checks the connected mailbox. `ingest.py` retrieves emails from `placementsupport@pes.edu` and `pesuplacements@pes.edu` within the last 30 days, including read messages.

The reader follows all result pages, selects plain text within alternative groups, and uses HTML fallback with link URLs preserved. Separate multipart body sections are retained; attachments are excluded. Full selected bodies and message metadata are saved to `component1_gmail/data/<message_id>.json`. Existing files are skipped on later runs. The verified repeat run reported `0 saved, 239 already downloaded`.

Temporary API failures are retried up to seven times with randomized exponential backoff. Exhausted retries stop the run; previously saved records can be skipped on restart. File writes are not atomic, and existing records are not validated before skipping. Downloading an email does not classify it or sync it to Notion. Other sources and the company allowlist remain planned.

## Notes

`profile_state.json`, `preferences.json`, and resume PDFs are gitignored — they contain personal data. `preferences.example.json` is included as a template.

Gmail `credentials.json`, `token.json`, and the entire `component1_gmail/data/` directory are also gitignored. Do not commit OAuth credentials or downloaded email records.
