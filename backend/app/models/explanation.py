from pydantic import BaseModel, Field


class AssessmentExplanation(BaseModel):
    """LLM-generated explanation constrained to deterministic evidence."""

    summary: str = Field(min_length=1, max_length=1000)
    rationale: str = Field(min_length=1, max_length=2000)
    caveats: list[str] = Field(default_factory=list, max_length=8)
    evidence_ids: list[str] = Field(default_factory=list, max_length=20)
