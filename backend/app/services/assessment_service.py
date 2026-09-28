from __future__ import annotations

from datetime import date, datetime
from typing import Any

from backend.app.models.evidence import EvidenceRecord
from backend.app.models.memory import MemoryEvidence
from backend.app.services.evidence_service import EvidenceService


class AssessmentService:
    """Coordinates memory retrieval and deterministic evidence classification."""

    def __init__(self, evidence_service: EvidenceService | None = None) -> None:
        self._evidence_service = evidence_service or EvidenceService()

    async def assess_vehicle(
        self,
        *,
        vehicle_id: str,
        issue_key: str,
        memory_service: Any,
    ):
        recalled = await memory_service.recall_vehicle_history(vehicle_id, issue_key)
        records = [self._to_evidence_record(item) for item in recalled]
        assessment = self._evidence_service.classify(issue_key, records)
        return assessment, "available" if recalled else "empty"

    @staticmethod
    def _to_evidence_record(item: MemoryEvidence) -> EvidenceRecord:
        metadata = item.metadata or {}
        source_type = metadata.get("source_type")
        polarity = metadata.get("polarity", "unresolved")
        issue_key = metadata.get("issue_candidate")
        observed_at = AssessmentService._parse_date(
            metadata.get("observed_at")
            or item.occurred_start
            or item.mentioned_at
        )
        if not source_type or polarity not in {"supporting", "contradicting", "unresolved"}:
            polarity = "unresolved"
        if not issue_key:
            issue_key = "unknown"

        return EvidenceRecord(
            evidence_id=item.memory_id or str(metadata.get("report_id", "")),
            issue_key=issue_key,
            source_id=str(metadata.get("source_id", "unknown")),
            source_type=source_type or "owner",
            polarity=polarity,
            observed_at=observed_at,
            text=item.text,
            dependency_group=metadata.get("dependency_group"),
        )

    @staticmethod
    def _parse_date(value: Any) -> date:
        if isinstance(value, datetime):
            return value.date()
        if isinstance(value, date):
            return value
        if isinstance(value, str) and value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return date.min
