import json
from datetime import datetime
from pathlib import Path

from parser import extract_text_from_pdf, file_hash, structure_resume_text
from schema import Preferences, ProfileState, ResumeRecord

BASE_DIR = Path(__file__).parent
# Path(__file__).parent gives us the folder store.py lives in, regardless of
# what directory you happen to run the script from. Using this instead of a
# hardcoded path or a relative "./" means the script works the same whether
# you run it from this folder or somewhere else entirely.

RESUMES_DIR = BASE_DIR / "resumes"
STATE_PATH = BASE_DIR / "profile_state.json"
PREFERENCES_PATH = BASE_DIR / "preferences.json"

def load_state() -> ProfileState:
    """Load profile_state.json if it exists, else return a fresh empty ProfileState."""
    if STATE_PATH.exists():
        return ProfileState.model_validate_json(STATE_PATH.read_text())
    return ProfileState()
    # model_validate_json() parses the JSON text AND validates it against the
    # schema in one step — if profile_state.json ever got manually edited into
    # something malformed, this would raise a clear error here rather than
    # silently loading broken data.

def save_state(state: ProfileState) -> None:
    """Write a ProfileState object to profile_state.json as pretty-printed JSON."""
    STATE_PATH.write_text(state.model_dump_json(indent=2))
    # model_dump_json() is the inverse of model_validate_json() — turns the
    # Pydantic object back into a JSON string. indent=2 just makes the file
    # human-readable if you ever open it to check what's in there.

def load_preferences() -> Preferences:
    """Load preferences.json if it exists, else return empty defaults."""
    if PREFERENCES_PATH.exists():
        return Preferences.model_validate_json(PREFERENCES_PATH.read_text())
    return Preferences()
    # Same pattern as load_state() -- if the file doesn't exist yet (you
    # haven't filled it in), we return sensible empty defaults rather than
    # erroring, so the rest of the pipeline can still run.

def sync_resumes(verbose: bool = True) -> ProfileState:
    """
    Scan resumes/ , re-parse any file that is new or changed, drop records 
    deleted files, refresh preferences, and save the results to profile_state.json.
    """

    state = load_state()
    seen_filenames = set()
    # We track every filename we actually find in resumes/ this run, so that
    # afterward we can figure out which OLD records (from a previous run)
    # correspond to files that no longer exist -- and remove them.

    for pdf_path in sorted(RESUMES_DIR.glob("*.pdf")):
        filename = pdf_path.name
        seen_filenames.add(filename)
        current_hash = file_hash(str(pdf_path))

        existing = state.resumes.get(filename)
        if existing and existing.file_hash == current_hash:
            # Same filename, same hash as last time -> content hasn't
            # changed -> skip re-parsing entirely. This is the whole point
            # of hashing: no wasted Ollama calls on unchanged files.
            if verbose:
                print(f"[skip] {filename} -- unchanged")
            continue

        if verbose:
            action = "update" if existing else "new"
            print(f"[{action}] {filename} -- parsing...")

        raw_text = extract_text_from_pdf(str(pdf_path))
        profile = structure_resume_text(raw_text)
        state.resumes[filename] = ResumeRecord(
            filename=filename,
            file_hash=current_hash,
            last_parsed=datetime.now(),
            profile=profile,
        )

    # Drop records for resumes that were removed from the folder since last run
    removed = set(state.resumes.keys()) - seen_filenames
    for filename in removed:
        if verbose:
            print(f"[remove]{filename} -- no longer in resumes/")
        del state.resumes[filename]

    state.preferences = load_preferences()
    state.last_updated = datetime.now()
    save_state(state)
    return state