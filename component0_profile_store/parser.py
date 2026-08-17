import pdfplumber
import hashlib
import requests
import json
from schema import ResumeProfile

MODEL = "llama3.1:8b"

STRUCTURING_SYSTEM_PROMPT = """You convert raw resume text into structured JSON.
Output ONLY a single JSON object matching this shape, with no preamble, no
markdown fences, and no commentary:

{
  "contact": {"name": str|null, "email": str|null, "phone": str|null,
              "location": str|null, "linkedin": str|null, "github": str|null},
  "target_role_focus": str,
  "skills": {category: [skill, ...], ...},
  "experience": [{"organization": str, "role": str, "start_date": str|null,
                   "end_date": str|null, "bullets": [str, ...]}, ...],
  "projects": [{"name": str, "tech_stack": [str, ...], "bullets": [str, ...],
                "link": str|null}, ...],
  "education": [{"institution": str, "credential": str, "start_date": str|null,
                  "end_date": str|null, "score": str|null}, ...],
  "certifications": [str, ...],
  "leadership_and_activities": [str, ...]
}

Rules:
- Preserve bullet text close to verbatim; do not invent metrics or claims not in the source.
- If a field genuinely isn't present or is blank, use null (for scalars) or [] / {} (for lists/dicts). Never return an empty string "" — use null instead.
- Infer target_role_focus from skills/projects emphasis, not just section titles,
  e.g. "Software Engineering", "Data Science / ML", "GenAI", "Cloud Computing".
"""
# We spell out the exact JSON shape in the prompt itself, matching our
# Pydantic schema field-for-field. Local models follow explicit shape
# instructions much more reliably than vague ones like "return structured
# resume data" — the more literal we are, the fewer parsing failures we get.

def structure_resume_text(raw_text: str) -> "ResumeProfile":
    """Send raw resume text to the local Ollama model, get back a validated ResumeProfile."""
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": MODEL,
            "system": STRUCTURING_SYSTEM_PROMPT,
            "prompt": raw_text,
            "format": "json", # tells Ollama to constrain output to valid JSON
            "stream": False, # we want the full response at once, not a token stream
        }
    )
    response.raise_for_status()
    # raise_for_status() throws immediately if Ollama returns an HTTP error
    # (e.g. the model isn't pulled, or the server isn't running) — better to
    # fail loudly here than get a confusing error two lines later.

    raw_output = response.json()["response"]
    # Ollama's /api/generate always wraps the model's actual text output
    # inside a "response" key of its own JSON envelope — this line unwraps that.

    cleaned = raw_output.strip()
    if cleaned.startswith("```"):
        # Defensive cleanup: even with format="json", a model occasionally
        # wraps output in markdown fences out of habit. Strip them if present.
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:].strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        # If parsing still fails, print what we actually got — invaluable
        # for debugging prompt issues later, rather than a bare traceback.

        print("--- RAW MODEL OUTPUT (failed to parse as JSON) ---")
        print(raw_output)
        raise

    return ResumeProfile.model_validate(data)

def extract_text_from_pdf(pdf_path: str) -> str:
    """Pull raw text out of every page of a PDF and join it into one string."""
    with pdfplumber.open(pdf_path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)
    # page.extract_text() can return None for a blank/image-only page —
    # the "or ''" guards against that so we don't crash trying to join None
    # into the string.

def file_hash(pdf_path: str) -> str:
    """Compute a SHA-256 hash of a file's raw bytes, for change detection."""
    with open(pdf_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()
    # Hashing the bytes (not reading text) means ANY change to the file
    # produces a different hash — even formatting changes that don't alter
    # extracted text. Safer than comparing extracted text strings, and much
    # cheaper than comparing full ResumeProfile objects.