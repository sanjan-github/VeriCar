from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class VehicleReport:
    report_id: str
    vin: str
    source_id: str
    source_type: str
    text: str
    observed_at: datetime


@dataclass(frozen=True)
class MemoryEvidence:
    memory_id: str
    text: str
    memory_type: str | None = None
    context: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    occurred_start: str | None = None
    occurred_end: str | None = None
    mentioned_at: str | None = None
    document_id: str | None = None
    chunk_id: str | None = None
