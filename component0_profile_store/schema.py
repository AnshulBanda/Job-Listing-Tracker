from __future__ import annotations
# ^ lets us use "list[str]" and forward references without import headaches
#   on older Python versions — harmless to keep even on newer ones.

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ContactInfo(BaseModel):
    """Basic identity info pulled from the top of a resume."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    # All Optional because a resume might not list every field (e.g. no GitHub
    # link on some versions) — we don't want validation to fail over that.


class ExperienceEntry(BaseModel):
    """One job/internship entry in the Experience section."""
    organization: str
    role: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    # end_date is Optional because current roles often just say "Present"
    # or have no end date at all — we store whatever string is there, or None.
    bullets: list[str] = Field(default_factory=list)
    # default_factory=list (NOT "= []") avoids Python's shared-mutable-default
    # bug: with "= []", every ExperienceEntry would share the SAME list object
    # in memory, so appending to one instance's bullets would silently leak
    # into every other instance. default_factory gives each instance its own list.


class ProjectEntry(BaseModel):
    """One project entry, e.g. 'Prob.lm' or 'J-Orchestrator'."""
    name: str
    tech_stack: list[str] = Field(default_factory=list)
    bullets: list[str] = Field(default_factory=list)
    link: Optional[str] = None  # GitHub link, if the resume includes one


class EducationEntry(BaseModel):
    """One school/degree entry."""
    institution: str
    credential: str  # e.g. "B.Tech in Computer Science"
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    score: Optional[str] = None  # CGPA, percentage — kept as a string since
    # the format varies ("7.41/10" vs "81%") and we don't need to do math on it

class ResumeProfile(BaseModel):
    """Everything structured out of a single resume file."""
    contact: ContactInfo

    target_role_focus: str = Field(
        description="Inferred primary role focus of this resume version, "
        "e.g. 'Software Engineering', 'Data Science / ML', 'GenAI', 'Cloud'"
    )
    # We don't set this manually per file — the LLM infers it from which
    # skills/projects a resume emphasizes. This is what lets Component 3
    # later pick "use the Data Science resume for this posting, not the
    # SWE one" without you tagging every file by hand.

    skills: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Category name -> list of skills, e.g. {'Languages': [...], 'ML': [...]}",
    )
    # Kept as a dict-of-categories (not one flat list) because your resumes
    # already group skills this way ("Languages:", "AI & ML:", etc.) —
    # preserving that structure keeps more signal for matching later.

    experience: list[ExperienceEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    leadership_and_activities: list[str] = Field(default_factory=list)

class ResumeRecord(BaseModel):
    """One tracked resume file: its parsed profile plus change-detection metadata."""
    filename: str
    file_hash: str
    # A SHA-256 hash of the PDF's bytes. We compare this hash, not the file's
    # last-modified timestamp, because timestamps change if you just move or
    # re-save a file with no real content change — hashing only changes if
    # the actual bytes changed, so we don't waste an LLM call re-parsing
    # something identical.
    last_parsed: datetime
    profile: ResumeProfile

class Preferences(BaseModel):
    """Stated preferences not derivable from a resume. You edit this directly."""
    target_roles: list[str] = Field(default_factory=list)
    must_have_criteria: list[str] = Field(default_factory=list)
    preferred_locations: list[str] = Field(default_factory=list)
    companies_to_avoid: list[str] = Field(default_factory=list)
    min_stipend_or_ctc: Optional[str] = None
    notes: Optional[str] = None

class ProfileState(BaseModel):
    """The full current profile state that Component 3 (Matching) reads from."""
    resumes: dict[str, ResumeRecord] = Field(default_factory=dict)
    # Keyed by filename, e.g. {"Anshul_Banda_Resume.pdf": ResumeRecord(...)}
    # A dict (not a list) so we can look up / overwrite a specific resume's
    # record by filename in O(1) when re-parsing it.

    preferences: Preferences = Field(default_factory=Preferences)
    last_updated: datetime = Field(default_factory=datetime.now)

