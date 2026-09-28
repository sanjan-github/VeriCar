from __future__ import annotations

import asyncio
from datetime import date, datetime
from typing import Any

from backend.app.models.evidence import EvidenceRecord, SourceHistory
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
        source_history: dict[str, SourceHistory] = {}
        source_types: dict[str, str] = {}
        for item in recalled:
            metadata = item.metadata or {}
            source_id = str(metadata.get("source_id", "unknown"))
            source_type = metadata.get("source_type")
            if source_id != "unknown" and source_type:
                source_types.setdefault(source_id, source_type)

        source_ids = list(source_types)
        histories = await asyncio.gather(
            *(
                memory_service.recall_source_history(
                    source_id,
                    "historical report outcomes corroborated contradicted unresolved",
                )
                for source_id in source_ids
            )
        )
        for source_id, history in zip(source_ids, histories):
            source_history[source_id] = self._source_history(
                source_id,
                source_types[source_id],
                history,
            )

        records = [
            self._to_evidence_record(
                item,
                source_history.get(
                    str((item.metadata or {}).get("source_id", "unknown"))
                ),
            )
            for item in recalled
        ]
        assessment = self._evidence_service.classify(issue_key, records)
        return assessment, "available" if recalled else "empty"

    @staticmethod
    def _source_history(
        source_id: str,
        source_type: str,
        memories: list[MemoryEvidence],
    ) -> SourceHistory:
        """Count explicit outcome events once per report, without inferring from claim polarity."""
        outcomes: dict[str, tuple[str, str]] = {}
        for item in memories:
            metadata = item.metadata or {}
            event_source_id = metadata.get("source_id")
            if event_source_id is not None and str(event_source_id) != source_id:
                continue
            report_id = metadata.get("resolved_report_id") or metadata.get("report_id")
            outcome = (
                metadata.get("resolution_status")
                or metadata.get("relationship_status")
                or metadata.get("outcome")
            )
            if not report_id or outcome not in {"corroborated", "contradicted", "unresolved"}:
                continue
            recorded_at = str(
                metadata.get("recorded_at")
                or item.mentioned_at
                or item.occurred_end
                or item.occurred_start
                or ""
            )
            resolved_at = str(metadata.get("resolved_at") or "")
            timestamp = f"{recorded_at}|{resolved_at}"
            current = outcomes.get(str(report_id))
            if current is None or timestamp >= current[1]:
                outcomes[str(report_id)] = (outcome, timestamp)

        corroborated = sum(outcome == "corroborated" for outcome, _ in outcomes.values())
        contradicted = sum(outcome == "contradicted" for outcome, _ in outcomes.values())
        return SourceHistory(
            source_id=source_id,
            source_type=source_type,
            resolved_reports=corroborated + contradicted,
            corroborated=corroborated,
            contradicted=contradicted,
        )

    @staticmethod
    def _to_evidence_record(
        item: MemoryEvidence,
        source_history: SourceHistory | None = None,
    ) -> EvidenceRecord:
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
            source_history=source_history,
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
