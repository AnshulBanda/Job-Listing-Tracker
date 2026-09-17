from pydantic import BaseModel, ConfigDict, Field


class JobDetails(BaseModel):
    """Facts explicitly stated in the supplied job text."""

    model_config = ConfigDict(extra="forbid", strict=True)

    company: str | None = None
    role: str | None = None
    location: str | None = None
    employment_type: str | None = None

    responsibilities: list[str] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)

    experience_requirements: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    eligibility_requirements: list[str] = Field(default_factory=list)

    compensation: str | None = None
    application_deadline: str | None = None