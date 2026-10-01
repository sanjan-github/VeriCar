from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


SourceKind = Literal["synthetic", "official", "government", "commercial", "user", "unknown"]
Reliability = Literal["high", "medium", "low", "unknown"]
EvidenceScope = Literal["vehicle", "model", "unknown"]


@dataclass(frozen=True)
class DataSource:
    """Provenance metadata for information supplied by a data provider."""

    source_id: str
    name: str
    kind: SourceKind
    url: str | None = None
    description: str | None = None

    def to_record(self) -> dict[str, str | None]:
        return {
            "source_id": self.source_id,
            "name": self.name,
            "kind": self.kind,
            "url": self.url,
            "description": self.description,
        }


@dataclass(frozen=True)
class ProviderResult:
    """A provider response with explicit availability and provenance."""

    status: Literal["FOUND", "NOT_FOUND", "UNAVAILABLE", "ERROR"]
    source: DataSource
    data: object | None = None
    message: str | None = None
    source_reliability: Reliability = "unknown"
    evidence_confidence: Reliability = "unknown"
    evidence_scope: EvidenceScope = "unknown"

    @property
    def available(self) -> bool:
        return self.status in {"FOUND", "NOT_FOUND"}

    @property
    def found(self) -> bool:
        return self.status == "FOUND"
