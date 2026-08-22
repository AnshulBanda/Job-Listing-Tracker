# Project Checkpoints — JobsApplier

**How to use this doc:** paste this whole file into a new chat when picking this project back up. It captures exact current state, decisions made, and what’s next — so you don’t have to re-explain anything. Update it as you go.

**Repo:** [https://github.com/AnshulBanda/Job-Listing-Tracker](https://github.com/AnshulBanda/Job-Listing-Tracker)

See also: `project_blueprint.md` (original architecture doc — decisions there still hold unless overridden below). A `project_blueprint.md` v2 was generated alongside this checkpoint to reflect two scope additions (PES Placements source, Shortlist tracking) — use that version going forward.

---

## Working Style (Important — Re-read This First)

* I want to **type and understand every line myself**, not receive ready-to-run files. Explain the *why* before the code, give small pieces at a time, wait for confirmation before moving on.
* Include inline comments in code explaining what non-obvious lines do (e.g. why `default_factory=list` not `= []`, why hashing not mtime, etc.) — I want to be able to re-read this code later and still understand it without re-asking.
* I’m on **Windows / PowerShell**, using `py` (not `python3` — that alias is broken on my machine).
* Git commit messages: single short line only, never multi-line.

---

## Environment

* **Python:** 3.14
* **Virtual environment:** one shared venv at the **project root** (`JobsApplier/venv`) — not per-component.
* Activate with:

```powershell
.\venv\Scripts\Activate.ps1
```

from the project root.

* **LLM:** Ollama, local, model `llama3.1:8b`

  * Not a paid API.
  * Chosen over Anthropic/Gemini/Groq because it’s free, has no rate limits, is fully offline, and is consistent with other portfolio projects (Prob.lm, NutriChat).
  * Must be running (`ollama serve`) before any resume parsing or matching step will work — a `requests.exceptions.ConnectionError` at `localhost:11434` means Ollama isn't up.

### Current Resume Files

Two resume PDFs currently exist in `component0_profile_store/resumes/`:

* `SWE_Resume.pdf`
* `DA_Resume.pdf`

More versions such as GenAI and Cloud are planned later. The code already supports multiple resumes.

### Notion Integration

* Integration created at [notion.so/my-integrations](https://www.notion.so/my-integrations), named "JobsApplier".
* A parent page exists in Notion (shared with the integration via "Add connections") to house the two databases.
* Credentials live in a **project-root `.env`** file (gitignored):

```
NOTION_TOKEN=<integration secret>
NOTION_PARENT_PAGE_ID=<32-char page ID, no dashes needed>
```

* ⚠️ An earlier integration secret was accidentally pasted into chat and was regenerated as a precaution. Never paste live secrets into chat again — describe values, don't paste them.

---

## Project Structure So Far

```text
JobsApplier/                         <- repo root, git initialized here
├── venv/                            <- shared venv, gitignored
├── .env                             <- Notion secrets, gitignored
├── .gitignore
├── README.md
├── project_blueprint.md             <- original architecture doc (see v2 note above)
├── project_checkpoints.md           <- this file
├── requirements.txt
├── component0_profile_store/
│   ├── schema.py                    <- Pydantic models, DONE
│   ├── parser.py                    <- PDF extraction + Ollama call, DONE
│   ├── store.py                     <- sync_resumes(), DONE
│   ├── watcher.py                   <- watchdog auto-trigger, DONE (merged via feature/component0-watcher PR)
│   ├── preferences.example.json     <- template, committed
│   ├── preferences.json             <- real prefs, gitignored
│   ├── profile_state.json           <- generated output, gitignored
│   └── resumes/
│       ├── .gitkeep
│       ├── SWE_Resume.pdf           <- gitignored
│       └── DA_Resume.pdf            <- gitignored
└── component_notion/
    └── setup_databases.py           <- IN PROGRESS (see below)
```

---

## Status

* [x] Alerts on job sources — **not yet done** (LinkedIn + Naukri set up so far, of 9 planned sources — see blueprint v2)
* [x] Resume(s) + preferences provided
* [x] **Component 0 — Resume/Profile Store: fully working, tested end-to-end on Windows, pushed to GitHub**

  * `schema.py`, `parser.py`, `store.py` — built and verified (see prior checkpoint history for details).
  * `watcher.py` — **DONE.** `watchdog`-based handler watching `resumes/` for `.pdf` `on_created`/`on_modified` events, calling `sync_resumes()`. Handles Windows file-lock races (`PermissionError`, retried up to 5x/0.5s apart) and Ollama-down (`requests.exceptions.ConnectionError`, logged and skipped — **not auto-retried later**, needs the file re-touched once Ollama's back up). Path resolved via `pathlib` relative to the script's own location, not a relative string, so it runs correctly regardless of working directory.
  * Pushed on branch `feature/component0-watcher`, PR opened (not yet confirmed merged — confirm merge status on resume).
* [~] **Notion databases — IN PROGRESS, code partially written, nothing run yet.**

  * Integration + parent page set up (see Environment section above).
  * `component_notion/setup_databases.py` started: imports, `.env` loading, and the `Job Opportunities` schema dict + `create()` call are drafted (see "Notion Schema Decisions" below for exact fields).
  * `Placement Calendar` schema dict + `create()` call also drafted, including today's new `Shortlisted` field.
  * **Not yet decided:** one-way vs. two-way relation for `Linked Opportunity` (leaning one-way/`single_property` as the simpler default, but not locked in).
  * **Nothing has been typed into the file yet for either database** — pick this back up before touching new code, to avoid inconsistent state.
* [ ] Gmail ingestion (Component 1) — needs updating for the 9th source (PES Placements) once built
* [ ] Extraction step (Component 2)
* [ ] Matching step (Component 3)
* [ ] Notion sync (Component 4)
* [ ] Orchestration (Component 5)

---

## Decisions Made Along the Way

These decisions were made after the original blueprint and should take precedence where they differ.

### 1. Missing Scalar Fields

The LLM prompt requires the model to return `null` for missing scalar fields, never `""` (empty string).

### 2. Preferences Are Hand-Edited

`preferences.json` is **hand-edited by you** and is never written by code. `store.py` only reads it through `load_preferences()`.

### 3. Shared Virtual Environment

One shared `venv/` and `requirements.txt` at the repository root, reused by all components. No per-component venvs.

### 4. watcher.py Design Choices

* Filters to `*.pdf` only; calls `sync_resumes()` on every matching event with **no debounce** — relies on `sync_resumes()`'s existing hash-based idempotency to no-op safely on duplicate/noisy events.
* Resolves `resumes/` via `Path(__file__).resolve().parent / "resumes"` rather than a plain relative string, so it works regardless of the directory it's run from.
* Retries on `PermissionError` (Windows file-lock races during copy operations); catches `requests.exceptions.ConnectionError` separately (Ollama down) and logs + skips rather than retrying, since that failure mode won't self-resolve in seconds.

### 5. Notion Database Setup Method

Built as a **Python script using `notion-client`**, not the Notion MCP connector and not manual UI creation — reusable if the databases ever need recreating.

### 6. Notion Schema Decisions (Job Opportunities)

* **Fit Score → `number` type** (1–10 range), not `select`. Easier for the LLM matching step to output directly; sorts/filters cleanly; avoids brittle string-mapping from LLM output to fixed categories.
* **Source → free-text (`rich_text`)**, not a locked `select` with the fixed source list. Needed because company-allowlist and PES Placements entries use arbitrary/specific names as the Source value, not a fixed set.
* **Date Added → manually-set `date` field**, not Notion's automatic `created_time` — the sync script sets this explicitly rather than relying on Notion's own page-creation timestamp.
* **Company** is the `title` property (not Role) — most natural anchor field for scanning entries.
* **Status** stays a `select` (New/Applied/Rejected/Interviewing/Offer) — genuinely a fixed, small, closed set, unlike Source.

### 7. Notion Schema Decisions (Placement Calendar)

* **Event** is the `title` property (e.g. `"OA — Company X"`); `Company` is `rich_text` here instead.
* **Date** field's built-in time component is used directly for test/interview timings — no separate time field needed.
* **New `Shortlisted` field** (`select`: Pending / Yes / No) — added to support round-by-round shortlist tracking (see scope addition below).
* **Each round of a multi-round process is its own separate row** (not one row updated in place) — preserves full history of every stage (OA → Interview 1 → Interview 2, etc.), all linked to the same Job Opportunities entry via the `Linked Opportunity` relation.
* **Relation direction (`single_property` vs `dual_property`) — not yet decided**, see Status section above.

---

## Scope Additions (Post-Blueprint)

These extend the original blueprint and are reflected in `project_blueprint.md` v2.

### A. College Placement Cell as a 9th Source

Track opportunities from PES University's own placement cell, via two known sender addresses:

* `placementsupport@pes.edu`
* `pesuplacements@pes.edu`

Treated as a 9th fixed recognized source ("PES Placements") in Component 1 (Ingestion) — same tier as the 8 job boards, **not** routed through the company-allowlist mechanism (that's reserved for arbitrary individual companies you subscribe to directly).

### B. Shortlist Tracking for Tests/Interviews

Added the `Shortlisted` field to Placement Calendar (see Decision #7 above) so that:

* If shortlisted → a new row gets added for the next round, with its own date/time.
* If not shortlisted → nothing further gets added; that row is simply marked `No` and the process ends there.

---

## Known Gotchas Hit While Building

### Windows

`python3` doesn’t work by default. Use `py` instead.

### Git Repository Location

`git init` was accidentally run inside `component0_profile_store/` at one point instead of the project root. Fixed by re-initializing Git at the root before the first commit. The repository root must be `JobsApplier/`, not `JobsApplier/component0_profile_store/`.

### GitHub Repository History

The GitHub repository was initially created with an auto-generated README, causing unrelated Git histories. Fixed with:

```powershell
git pull origin main --allow-unrelated-histories
```

### Windows File Locking During Copy

`watchdog`'s `on_created` can fire before Windows finishes writing a copied file, causing a `PermissionError` in `file_hash()`. Fixed with a retry loop (5 attempts, 0.5s apart) in `watcher.py`'s `_maybe_sync()`.

### Never Paste Live Secrets Into Chat

An integration secret was pasted into chat while setting up Notion. It was treated as compromised and regenerated immediately. Going forward, secrets get described (e.g. "I've set `NOTION_TOKEN` in `.env`"), never pasted verbatim.

---

## Next Step When Resuming

### Finish `component_notion/setup_databases.py`

1. Decide **one-way vs. two-way relation** for `Linked Opportunity` (open question — see Status above).
2. Type in the `Job Opportunities` schema dict + `notion.databases.create(...)` call (drafted, not yet entered).
3. Type in the `Placement Calendar` schema dict (including `Shortlisted`) + its `create()` call, using the `Job Opportunities` database ID for the relation field.
4. Run the script once, confirm both databases appear correctly in Notion with all fields and types as expected.
5. Commit + push on a new feature branch (e.g. `feature/notion-schema-setup`), open a PR — same flow as Component 0.

### After Notion Setup

Next priority is **Gmail ingestion (Component 1)** — now needs to account for **9 sources**, not 8, including the new PES Placements sender patterns. OAuth setup, pull script, and sender-pattern matching all still need building from scratch.
