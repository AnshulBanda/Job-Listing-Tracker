# Placement Tracker — Project Blueprint (v2)

A GenAI system that monitors job/internship alert emails, matches opportunities against your resume and preferences, and surfaces everything in Notion with a fit score, reasoning, and apply link — plus a calendar of tests/interviews/deadlines.

**How to use this doc:** Paste this whole file into a new chat as context when you're ready to build a given component. It's meant to replace re-explaining the project each time. Update the "Status" sections as pieces get built.

**v2 changes from the original blueprint:** added PES University's placement cell as a 9th monitored source (§3); added shortlist tracking to the Placement Calendar (§5); resolved the open Fit Score design question (§5); Source field is free text, not a locked category list (§5).

---

## 1. Goal

During placement season, automatically:
1. Detect new job/internship opportunities you're eligible for (via email alerts, not scraping)
2. Score each one against your resume + stated preferences, with a written reason
3. File every opportunity into Notion (sorted by score — nothing filtered out) with a direct apply link
4. Track deadlines, tests, and interview dates — including shortlist outcomes across multiple rounds — in a Notion calendar

---

## 2. Confirmed Decisions (do not re-litigate these — build against them)

| Decision | Choice | Why |
|---|---|---|
| Source of job postings | Email alerts, not scraping | LinkedIn/Glassdoor ToS prohibit scraping; email digests sidestep this entirely |
| Where it runs | Local script on your machine, scheduled/manual trigger | No cloud deployment complexity needed for MVP |
| Notification/tracking interface | Notion | You already use it |
| Filtering strategy | File **every** alert, sorted by match score — never silently drop one | Avoids missing a borderline-good opportunity |
| Monitored alert sources (9) | LinkedIn Jobs, Naukri.com, Cutshort, Unstop, Instahyre, RemoteOK, We Work Remotely, Glassdoor, PES Placements | See §3 |
| Manual-only source | Turing (apply once, get matched — no digest to parse, don't build ingestion for it) | Doesn't fit the alert-monitoring model |
| Excluded source | Internshala | Flagged by you as scam-prone; replaced by Cutshort |
| Company-specific alerts | Included, via allowlist | You subscribe directly on company career pages; you maintain a list of subscribed company sender addresses/domains for Component 1 to watch (not auto-classified — see §3a) |
| College placement cell | Included, as a fixed 9th source (not via allowlist) | PES University's placement office sends its own curated opportunities — distinct from individual company subscriptions, so it gets fixed sender-pattern treatment like the 8 job boards |
| Old spreadsheet tracker | Retired, no migration | Notion replaces it entirely; starting fresh with no imported data |
| Resume handling | Not one-time ingestion — system must re-read resumes when updated/added, and refresh matching accordingly | You'll add new resume versions and edit existing ones over time |
| Fit Score representation | Notion `number` type, 1–10 | Easier for the LLM matching step to output directly than mapping into fixed select categories; sorts/filters cleanly |
| Job Opportunities "Source" field | Free text (`rich_text`), not a locked category list | Needs to hold company-allowlist names and "PES Placements" alongside the 8 job board names — an open-ended set, not a fixed one |
| Shortlist tracking | Each interview/test round is its own Placement Calendar row, linked to the same opportunity, with a Shortlisted field (Pending/Yes/No) | Preserves full history of a multi-round process; a "No" simply ends the chain with no further rows added |

---

## 3. Monitored Alert Sources

Set up "email me new jobs" alerts for your target roles on all 9:

1. LinkedIn Jobs
2. Naukri.com
3. Cutshort
4. Unstop
5. Instahyre
6. RemoteOK
7. We Work Remotely
8. Glassdoor
9. PES Placements (college placement cell — see §3b)

The ingestion script needs to recognize each source's sender address/domain and typical subject-line pattern — collect a sample email from each once alerts start arriving, since parsing rules will differ per source.

### 3a. Company-Specific Alerts (Allowlist)

In addition to the 9 sources above, you can subscribe directly to individual companies' career-page job alerts (e.g. sign up for job alerts on a specific company's careers site). These come from arbitrary, per-company sender domains rather than a fixed known list, so they're handled differently:

- Maintain a simple list (e.g. a text file or a Notion database) of companies you've subscribed to, with their alert-sender address/domain
- Component 1 (Ingestion) checks incoming email senders against this allowlist, in addition to the 9 fixed source patterns
- When you subscribe to a new company's alerts, add it to the list — the pipeline won't auto-detect unrecognized senders (that would be the "classifier" approach, which was considered and deferred — see decisions table in §2)
- Once matched via the allowlist, these emails go through the same Extraction → Matching → Notion sync steps as any other source
- In Notion, these entries use the actual company name as the `Source` value (not a generic bucket)

### 3b. College Placement Cell (PES Placements)

PES University's placement office emails opportunities directly, from two known sender addresses:

- `placementsupport@pes.edu`
- `pesuplacements@pes.edu`

Unlike company-allowlist entries, this is treated as a **fixed, known source** (like the 8 job boards) rather than routed through the allowlist mechanism — Component 1 recognizes these two addresses directly. In Notion, these entries use `"PES Placements"` as the `Source` value.

---

## 4. Architecture

```
[Resume folder]                         [Gmail inbox]
      │                                        │
      ▼                                        ▼
[0. Profile Store] ◄── re-parses on   [1. Ingestion] — Gmail API pulls new/unread
  change/new file          ▲          alert emails matching known sender patterns
      │                    │          (9 fixed sources + allowlist)
      │            (feeds current                ▼
      │             profile state)      [2. Extraction] — LLM parses each raw email
      │                    │            into structured JSON:
      │                    │            { company, role, location, deadline,
      │                    │              apply_link, source, raw_snippet }
      │                    │                    │
      └────────────────────┴────────────────────▼
                                        [3. Matching] — LLM compares structured
                                        posting against CURRENT profile state,
                                        outputs: { fit_score, reasoning, flagged_gaps }
                                                 │
                                                 ▼
                                        [4. Notion sync] — pushes each opportunity
                                        into "Job Opportunities" database.
                                        Deadline/test/interview date → also written
                                        to "Placement Calendar", linked back.
                                        Shortlist outcomes add new calendar rows
                                        for subsequent rounds (see §5).
```

Everything after step 1 (Gmail pull) is source-agnostic — it operates on the extracted JSON, not raw email format. So component 1 is where most per-source complexity lives; components 2-4 are shared logic.

**Component 0 (Resume/Profile Store) is decoupled from the linear pipeline** — it's not a one-time ingestion step. It watches a resume folder (or is manually re-triggered) and re-parses whenever a resume is added or edited, updating the "current profile state" that Component 3 reads from. This means:
- Matching always uses your latest resume(s), not a stale snapshot from setup day
- Multiple resume versions can coexist (e.g. "data-analyst-resume.pdf", "swe-resume.pdf") — Component 3 should pick the best-fit resume per posting, not just use one default
- Past matches in Notion are NOT auto-recomputed retroactively when a resume changes (re-scoring old entries isn't in MVP scope) — only new incoming postings use the updated profile, unless you explicitly ask for a re-scan later

---

## 5. Notion Database Schemas

### Job Opportunities
| Field | Type | Notes |
|---|---|---|
| Company | Title | |
| Role | Text | |
| Source | Text | Free text — one of the 9 fixed sources, an allowlisted company name, or "PES Placements" |
| Fit Score | Number (1–10) | From matching step |
| Why it matched | Text | LLM reasoning, short |
| Flagged Gaps | Text | What's missing vs the posting's requirements |
| Deadline | Date | If extractable |
| Status | Select | New / Applied / Rejected / Interviewing / Offer |
| Resume Used | Text | Which resume version Component 3 picked as best-fit for this posting |
| Apply Link | URL | Direct from the alert email |
| Date Added | Date | Set explicitly by the sync script, not Notion's auto created-time |

### Placement Calendar
| Field | Type | Notes |
|---|---|---|
| Event | Title | e.g. "OA — Company X" |
| Company | Text | |
| Date | Date | Includes time-of-day for test/interview timings |
| Type | Select | Test / Interview / Application Deadline |
| Shortlisted | Select | Pending / Yes / No — tracks round-by-round outcome |
| Linked Opportunity | Relation | → Job Opportunities |
| Notes | Text | |

**Multi-round handling:** each round of an interview process (OA, Interview 1, Interview 2, etc.) is its own row, linked to the same Job Opportunities entry. If shortlisted, a new row is added for the next round with its own date/time. If not, the row is marked `No` and nothing further is added for that opportunity.

---

## 6. Inputs and Ongoing Setup

- **Resume file(s) (provided)** — the Overleaf LaTeX resume targeting data analyst/data science roles (PDF export), or whichever resume(s) you want the matching step to use. A folder of resumes is fine — Component 0 is designed to handle more than one and pick the best fit per posting
- **Stated preferences not already on the resume (provided)** — target roles, must-have criteria, locations, companies to avoid, minimum stipend/CTC if relevant
- **Company allowlist** — as you subscribe to individual companies' career alerts, a running list of company name + sender address/domain (can start empty and grow over time)
- **Sample emails from PES Placements** — once available, to confirm subject-line/body patterns for extraction, same as the other 8 sources
- Going forward: whenever you edit an existing resume or add a new one, drop it in the watched folder — you don't need to re-explain preferences each time, just the updated file(s)

---

## 7. Build Order (suggested — build/test one at a time, in separate chats if useful)

1. **Notion schema setup (complete)** — create the two databases through the Python `notion-client` setup script; verify field types and the one-way calendar relation. The Schedule calendar view was configured in the Notion UI.
2. **Resume/Profile Store (Component 0)** — parser that reads resume file(s) into structured profile data, re-runs on file add/change, stores "current profile state" somewhere the matching step can read from
3. **Gmail ingestion** — OAuth setup, pull script, sender-pattern matching for the 9 sources (start with whichever alerts arrive first)
4. **Extraction step** — LLM prompt that turns one raw alert email into the structured JSON schema in §4
5. **Matching step** — LLM prompt that scores structured postings against current profile state (needs Component 0 built first), picks best-fit resume if multiple exist
6. **Notion sync** — script that writes extraction + matching output into the two databases, including multi-round Placement Calendar rows and shortlist status updates
7. **Orchestration** — tie 3→6 into one runnable script (manual trigger first; consider cron/Task Scheduler later)

Each step can be built and tested independently against sample/mock data before wiring to the previous step's real output.

---

## 8. Tech Stack (proposed, confirm/adjust when building)

- **Language:** Python
- **Email:** Gmail API (`google-api-python-client`) + OAuth
- **LLM calls:** Ollama, local, `llama3.1:8b` (not a paid API — free, offline, no rate limits)
- **Notion:** `notion-client`, via a Python setup script (not the Notion MCP connector, not manual UI creation)
- **Scheduling:** manual run first; cron (Mac/Linux) or Task Scheduler (Windows) later if desired

---

## 9. Deferred / Future Consideration

- **Career-page scraping (e.g. Amazon Jobs)** — considered as a 10th+ ingestion source, to catch postings that don't come through email alerts. Not an Ollama-only solve — would need an actual scraper (requests/BeautifulSoup or Playwright for JS-heavy sites) feeding the existing Extraction step, since Ollama can't fetch live pages itself. Higher fragility than email (DOM structure breaks silently on redesign) vs. company-specific email alerts. **Decision: deferred.** First check whether target companies (starting with Amazon) offer a "job alerts" email subscription on their careers page — if so, that fits the existing Component 1 allowlist mechanism with zero new code. Only build a real scraper later, after Gmail ingestion (the 9 fixed sources + allowlist) is fully working end-to-end, and check for a stable ATS JSON API (Greenhouse/Lever/Workday) before defaulting to raw DOM scraping.

## 10. Status Tracker (updated 2026-09-05)

- [ ] Alerts set up on all 9 sources (LinkedIn + Naukri done so far)
- [x] Resume(s) + preferences provided
- [x] Notion databases created and verified; one-way relation and Schedule view configured — see [checkpoint.md](checkpoint.md)
- [x] Resume/Profile Store (re-parses on update) working — includes `watcher.py`
- [ ] Gmail ingestion working
- [ ] Extraction step working
- [ ] Matching step working
- [ ] Notion sync working
- [ ] End-to-end orchestration script working

## 11. Implemented Notion Setup Details

- `component_notion/setup_databases.py` creates Job Opportunities and Placement Calendar under the configured Placement Tracker page.
- Schema properties are supplied through `initial_data_source.properties`. Relations target the Job Opportunities `data_source_id`.
- `Linked Opportunity` uses `single_property` (one-way). Each event is a separate row; several events can occur on the same date at different times. The Date property includes time when known, without a separate Time field.
- The script searches all batches of direct child blocks by exact database title and reuses matches on sequential reruns. It does not migrate existing schemas or protect against concurrent runs, duplicate titles, or renamed databases.
- The user created a Schedule calendar view based on Date and confirmed two test events appeared on the same date.
- Database setup is complete; automated Notion entry synchronization is still a future component.
