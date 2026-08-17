# Project Checkpoints — JobsApplier

**How to use this doc:** paste this whole file into a new chat when picking this project back up. It captures exact current state, decisions made, and what’s next — so you don’t have to re-explain anything. Update it as you go.

**Repo:** [https://github.com/AnshulBanda/Job-Listing-Tracker](https://github.com/AnshulBanda/Job-Listing-Tracker)

See also: `project_blueprint.md` (original architecture doc — decisions there still hold unless overridden below).

---

## Working Style (Important — Re-read This First)

* I want to **type and understand every line myself**, not receive ready-to-run files. Explain the *why* before the code, give small pieces at a time, wait for confirmation before moving on.
* Include inline comments in code explaining what non-obvious lines do (e.g. why `default_factory=list` not `= []`, why hashing not mtime, etc.) — I want to be able to re-read this code later and still understand it without re-asking.
* I’m on **Windows / PowerShell**, using `py` (not `python3` — that alias is broken on my machine).

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

### Current Resume Files

Two resume PDFs currently exist in `component0_profile_store/resumes/`:

* `SWE_Resume.pdf`
* `DA_Resume.pdf`

More versions such as GenAI and Cloud are planned later. The code already supports multiple resumes.

---

## Project Structure So Far

```text
JobsApplier/                         <- repo root, git initialized here
├── venv/                            <- shared venv, gitignored
├── .gitignore
├── README.md
├── project_blueprint.md             <- original architecture doc
├── project_checkpoints.md           <- this file
├── requirements.txt
└── component0_profile_store/
    ├── schema.py                    <- Pydantic models, DONE
    ├── parser.py                    <- PDF extraction + Ollama call, DONE
    ├── store.py                     <- sync_resumes(), DONE
    ├── preferences.example.json     <- template, committed
    ├── preferences.json             <- real prefs, gitignored
    ├── profile_state.json            <- generated output, gitignored
    └── resumes/
        ├── .gitkeep
        ├── SWE_Resume.pdf            <- gitignored
        └── DA_Resume.pdf             <- gitignored
```

---

## Status

* [x] Alerts on 8 job sources — **not yet done**
* [x] Resume(s) + preferences provided
* [x] **Component 0 — Resume/Profile Store: fully working, tested, committed**

  * `schema.py` — `ContactInfo`, `ExperienceEntry`, `ProjectEntry`, `EducationEntry`, `ResumeProfile`, `ResumeRecord`, `Preferences`, `ProfileState` — all built and verified.
  * `parser.py` — `extract_text_from_pdf()`, `file_hash()`, `structure_resume_text()` (calls Ollama `/api/generate` with `format: "json"`) — all built and verified against both real resumes.
  * `store.py` — `load_state()`, `save_state()`, `load_preferences()`, `sync_resumes()` — all built and verified, including hash-based skip-if-unchanged behavior:

    * First run parses both files.
    * Second run skips both.
    * Editing one file re-parses only that file.
  * **Not yet built: `watcher.py`** — the `watchdog`-based auto-trigger so `sync_resumes()` runs automatically on file save instead of manually. This is the one remaining piece of Component 0.
* [ ] Notion databases created
* [ ] Gmail ingestion (Component 1)
* [ ] Extraction step (Component 2)
* [ ] Matching step (Component 3)
* [ ] Notion sync (Component 4)
* [ ] Orchestration (Component 5)

---

## Decisions Made Along the Way

These decisions were made after the original blueprint and should take precedence where they differ.

### 1. Missing Scalar Fields

The LLM prompt requires the model to return `null` for missing scalar fields, never `""` (empty string).

This keeps the representation of “field not found” consistent for downstream processing.

### 2. Preferences Are Hand-Edited

`preferences.json` is **hand-edited by you** and is never written by code.

`store.py` only reads it through:

```python
load_preferences()
```

### 3. Shared Virtual Environment

There is **one shared `venv/` and `requirements.txt` at the repository root**, reused by all future components.

There will not be one virtual environment per component.

---

## Known Gotchas Hit While Building

### Windows

`python3` doesn’t work by default.

Use:

```powershell
py
```

instead.

### Git Repository Location

`git init` was accidentally run inside `component0_profile_store/` at one point instead of the project root.

This was fixed by re-initializing Git at the root before the first commit.

The repository root must be:

```text
JobsApplier/
```

not:

```text
JobsApplier/component0_profile_store/
```

### GitHub Repository History

The GitHub repository was initially created with an auto-generated README, which caused unrelated Git histories.

This was fixed with:

```powershell
git pull origin main --allow-unrelated-histories
```

---

## Next Step When Resuming

### Build `watcher.py`

Build a `watchdog`-based script that watches:

```text
component0_profile_store/resumes/
```

and automatically calls:

```python
sync_resumes()
```

whenever a resume file is added or changed.

The goal is to eliminate the need to manually run the sync command after every resume update.

This will **finish Component 0**.

### After Component 0

The next priority is **Notion schema setup** (§7 of the blueprint).

This was deliberately chosen to happen **before Gmail ingestion**, because the Notion schema has no dependency on Gmail and establishing the destination structure first will make the later ingestion → extraction → matching → sync pipeline easier to design.
