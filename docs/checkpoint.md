# JobsApplier — Current Project Checkpoint

Updated: 2026-09-05

Repository: https://github.com/AnshulBanda/Job-Listing-Tracker

Architecture and scope: [blueprint.md](blueprint.md). This checkpoint replaces the older root-level `project_checkpoint.md` and incorporates the newer supplied checkpoint plus the verified Notion setup work.

## Working style

- The user prefers to type and understand implementation code: explain why, give small pieces with useful inline comments, and wait between steps.
- Windows / PowerShell; use `py` or the project venv executable, not `python3`.
- Git commit messages should be one short line.
- The user will create the new branch, commit, and push this milestone themselves. No commit or push was performed by the assistant.
- Never put live credentials in chat or tracked files. An earlier Notion secret was regenerated after accidental disclosure.

## Environment

- Python 3.14 with one shared `venv/` at the project root.
- Ollama runs locally at `localhost:11434`, using `llama3.1:8b`; parsing requires the service and model to be available.
- `pdfplumber` extracts resume text; Pydantic validates structured profiles.
- Installed Notion SDK during verification: `notion-client` 3.1.0, default API version `2025-09-03`.
- Root `.env` is gitignored and holds `NOTION_TOKEN` and `NOTION_PARENT_PAGE_ID`.
- The Notion integration is named JobsApplier. Its configured parent page is named Placement Tracker, and integration access was verified.

## Project layout

```text
JobsApplier/
├── docs/
│   ├── blueprint.md
│   └── checkpoint.md
├── README.md
├── requirements.txt
├── .gitignore
├── .env                            # local only, gitignored
├── venv/                           # shared environment, gitignored
├── component0_profile_store/
│   ├── schema.py
│   ├── parser.py
│   ├── store.py
│   ├── watcher.py
│   ├── preferences.example.json
│   ├── preferences.json            # hand-edited, gitignored
│   ├── profile_state.json          # generated, gitignored
│   └── resumes/                    # PDF files gitignored
└── component_notion/
    └── setup_databases.py
```

## Current status

- [x] Resume files and preferences provided.
- [x] Component 0 implemented and previously tested end-to-end on Windows.
- [x] Resume watcher implemented and merged in PR #1.
- [x] Notion parent page connected to JobsApplier.
- [x] Job Opportunities created; all 11 properties and Status options verified through the API.
- [x] Placement Calendar created; all 7 properties and select options verified through the API.
- [x] One-way Linked Opportunity relation verified against the Job Opportunities data source.
- [x] Sequential reruns reused both database IDs without creating new databases.
- [x] User configured a Schedule calendar view based on Date.
- [x] User confirmed two manual test events appeared on the same day after instructions to assign different times and link both to one opportunity. Event times and links were not independently read back.
- [ ] Alerts on all nine sources: only LinkedIn and Naukri confirmed so far.
- [ ] Gmail ingestion and OAuth (Component 1).
- [ ] Email extraction (Component 2).
- [ ] Matching (Component 3).
- [ ] Automated Notion entry synchronization (Component 4).
- [ ] Orchestration (Component 5).

The manual test entries were labelled TEST. Cleanup was suggested but has not been confirmed.

## Notion setup decisions and behavior

The setup is implemented in Python using `notion-client`; the user configured the calendar view in Notion's UI.

- Job Opportunities: Company (title), Role and Source (text), Fit Score (number), Why it matched and Flagged Gaps (text), Deadline (date), Status (select), Resume Used (text), Apply Link (URL), Date Added (date).
- Status options: New, Applied, Rejected, Interviewing, Offer.
- Placement Calendar: Event (title), Company (text), Date (date), Type (select), Shortlisted (select), Linked Opportunity (relation), Notes (text).
- Type options: Test, Interview, Application Deadline. Shortlisted options: Pending, Yes, No.
- Fit Score is intended to be 1–10; the number property itself does not enforce that range. Matching/sync must enforce it later.
- Source is free text for job boards, PES Placements, and allowlisted company names.
- Date Added will be assigned explicitly by synchronization code.
- Date supports time as well as day. No separate Time property is needed. Later extraction/sync must preserve known timezones and avoid inventing a time when only a date is provided.
- Each round is a separate event linked to its opportunity. A rejected shortlist outcome ends the documented round sequence; this automation is not yet implemented.
- Linked Opportunity uses `single_property`: a one-way relation, not a one-entry cardinality restriction.
- Database properties go under `initial_data_source.properties`. The earlier top-level `properties` argument was dropped by the installed SDK.
- The database is retrieved to obtain its data source ID. Exactly one data source is expected for Job Opportunities.
- `find_database_id()` paginates direct child blocks under the configured parent and returns the first exact-title match.
- Reuse does not verify or repair schemas. Database titles and parent placement must remain consistent; concurrent runs and duplicate titles are not handled.

Run from the project root:

```powershell
.\venv\Scripts\python.exe .\component_notion\setup_databases.py
```

## Profile store context

- Resumes are keyed by filename; SHA-256 detects byte changes. Unchanged files skip LLM parsing.
- `sync_resumes()` removes missing files from state, reloads hand-edited preferences, and writes the state file.
- Watcher handles PDF creation/modification with no debounce. It retries PermissionError five times with 0.5-second delays and logs/skips Ollama connection failures without later automatic retry.
- Watcher does not trigger on deletion, rename, preference-only changes, or startup.
- Local resumes include SWE_Resume.pdf, DA_Resume.pdf, and DA_Resume - Copy.pdf. The DA copy has identical bytes but its own parsed record; no cleanup has been performed.
- Current preferences: Software Engineer, Data Scientist, ML Engineer; Bengaluru or Remote; no additional must-have criteria, company exclusions, or minimum compensation set.
- Saved state validated through the existing loader. It uses Windows CP1252 rather than portable UTF-8; direct UTF-8 byte validation failed.
- Prompt asks for null rather than empty missing scalars, but saved output contains empty strings and link labels. Pydantic currently accepts these.
- Identical DA files produced different extracted details and inferred role focus. Hash caching is per filename, not across identical files.
- Ollama requests have no timeout; state writes are not atomic. These are known limitations, not fixes included in this milestone.

## Scope to preserve

- Ingest email alerts; file every opportunity and sort by score rather than silently filtering.
- Nine fixed sources: LinkedIn Jobs, Naukri, Cutshort, Unstop, Instahyre, RemoteOK, We Work Remotely, Glassdoor, PES Placements.
- PES senders: placementsupport@pes.edu and pesuplacements@pes.edu; fixed source, not company allowlist entries.
- Company-specific subscriptions use an explicit allowlist, with the company name as Source. Do not auto-classify arbitrary senders.
- Turing is manual-only; Internshala is excluded; no migration from the old spreadsheet.
- Multiple resume versions are supported. New opportunities use the latest profiles; retroactive rescoring is outside MVP scope.
- Career-page scraping is deferred until email ingestion works. Prefer company alerts, then stable ATS APIs before DOM scraping if revisited.

## Git state and next steps

Remote main was verified at `545261f`, the merge of PR #2 for the initial Notion setup. The Desktop checkout remains on `feature/notion-schema-setup`; the completed setup and documentation are uncommitted at the time of this checkpoint.

1. Review changes, create a new feature branch, commit this milestone, and push it. The user is handling Git commands.
2. Begin Gmail ingestion with Google Cloud project/OAuth setup and a minimal read-only email pull.
3. Add sender matching for nine fixed sources and company allowlist entries; collect sample alerts for extraction.
4. Continue extraction, matching, Notion sync, and orchestration after ingestion is working.
