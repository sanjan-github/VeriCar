from dataclasses import dataclass
from datetime import date
from typing import Literal


SourceType = Literal["owner", "buyer", "mechanic", "inspector"]
Polarity = Literal["supporting", "contradicting", "unresolved"]
EvidenceState = Literal[
    "insufficient_evidence",
    "limited_evidence",
    "moderate_evidence",
    "strong_evidence",
]


@dataclass(frozen=True)
class SourceHistory:
    source_id: str
    source_type: SourceType
    resolved_reports: int = 0
    corroborated: int = 0
    contradicted: int = 0


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    issue_key: str
    source_id: str
    source_type: SourceType
    polarity: Polarity
    observed_at: date
    text: str
    source_history: SourceHistory | None = None
    # A stable key for known dependent/copied evidence. None means no known dependency.
    dependency_group: str | None = None


@dataclass(frozen=True)
class EvidenceContribution:
    evidence_id: str
    source_id: str
    source_type: SourceType
    polarity: Polarity
    effective_reliability: float
    observed_at: date
    text: str


@dataclass(frozen=True)
class Assessment:
    issue_key: str
    state: EvidenceState
    confidence: float | None
    support_weight: float
    contradiction_weight: float
    independent_supporting_sources: int
    independent_contradicting_sources: int
    supporting_evidence: tuple[EvidenceContribution, ...]
    contradicting_evidence: tuple[EvidenceContribution, ...]
    unresolved_evidence: tuple[EvidenceContribution, ...]
