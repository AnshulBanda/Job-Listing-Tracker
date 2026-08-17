# JobsApplier (Placement Tracker)

A GenAI system that monitors job/internship alert emails, matches opportunities against my resume(s) and stated preferences, and surfaces everything in Notion with a fit score, reasoning, and apply link — plus a calendar of tests, interviews, and deadlines.

Built during campus placement season as a way to stop manually tracking every job alert across 8+ sources, while also serving as a portfolio project.

## Architecture

```text
[Resume folder]     [Gmail inbox]
       │                  │
       ▼                  ▼
[0. Profile Store] ◄── re-parses on ── [1. Ingestion]
       │                              pulls new alert emails
       │
       │ (feeds current profile state)
       ▼
[2. Extraction] — LLM parses each raw
email into structured JSON
       │
       ▼
[3. Matching] — LLM scores structured postings
against current profile state
       │
       ▼
[4. Notion sync] — writes opportunities + deadlines
into Notion databases
```

## Status

* [x] **Component 0 — Resume/Profile Store**: parses resume PDFs into structured JSON via a local LLM, with hash-based change detection so unchanged resumes are never re-parsed. Supports multiple resume versions (SWE, Data Science, and future GenAI/Cloud versions).
* [ ] **Component 1 — Gmail ingestion**
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
* **Planned:** Gmail API, Notion API, `watchdog` (folder watching)

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

## Notes

`profile_state.json`, `preferences.json`, and resume PDFs are gitignored — they contain personal data. `preferences.example.json` is included as a template.
