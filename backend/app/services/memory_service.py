from __future__ import annotations

from datetime import datetime, timezone

from backend.app.models.memory import MemoryEvidence, VehicleReport
from backend.app.repositories.hindsight_repository import HindsightRepository


VEHICLE_MISSION = (
    "Maintain an evidence-grounded history of one vehicle. "
    "Preserve contradictory reports and never treat an individual report "
    "as established mechanical truth."
)

SOURCE_MISSION = (
    "Maintain the historical reporting record for one source. "
    "Preserve corroborated, contradicted, and unresolved outcomes without "
    "treating source history as professional qualification."
)


class MemoryService:
    """Application-facing Hindsight memory service."""

    def __init__(self, repository: HindsightRepository) -> None:
        self._repository = repository

    async def ensure_vehicle_bank(self, vehicle_id: str) -> None:
        await self._repository.ensure_bank(
            bank_id=f"vehicle_{vehicle_id}",
            name=f"Vehicle history {vehicle_id}",
            mission=VEHICLE_MISSION,
        )

    async def ensure_source_bank(self, source_id: str) -> None:
        await self._repository.ensure_bank(
            bank_id=f"source_{source_id}",
            name=f"Source history {source_id}",
            mission=SOURCE_MISSION,
        )

    async def retain_report(self, report: VehicleReport):
        vehicle_result = await self.retain_vehicle_report(report)
        source_result = await self.retain_source_report(report)
        return vehicle_result, source_result

    async def retain_vehicle_report(self, report: VehicleReport):
        vehicle_id = report.vehicle_id
        if not vehicle_id:
            raise ValueError("VehicleReport.vehicle_id is required for vehicle memory.")
        await self.ensure_vehicle_bank(vehicle_id)
        return await self._repository.retain_report(report)

    async def retain_source_report(self, report: VehicleReport):
        await self.ensure_source_bank(report.source_id)
        return await self._repository.retain_source_report(report)

    async def resolve_source_outcomes(self, report: VehicleReport) -> None:
        """Record clear independent corroboration or contradiction events."""
        vehicle_id = report.vehicle_id
        if not vehicle_id:
            raise ValueError("VehicleReport.vehicle_id is required for source resolution.")
        if not report.issue_candidate or report.polarity == "unresolved":
            return

        memories = await self.recall_vehicle_history(
            vehicle_id,
            report.issue_candidate,
        )
        reports: dict[str, dict] = {}
        for item in memories:
            metadata = item.metadata or {}
            report_id = metadata.get("report_id")
            if not report_id:
                continue
            reports[str(report_id)] = metadata

        reports[report.report_id] = {
            "report_id": report.report_id,
            "vehicle_id": vehicle_id,
            "source_id": report.source_id,
            "source_type": report.source_type,
            "issue_candidate": report.issue_candidate,
            "polarity": report.polarity,
        }

        relevant = {
            report_id: metadata
            for report_id, metadata in reports.items()
            if metadata.get("issue_candidate") == report.issue_candidate
            and metadata.get("polarity") in {"supporting", "contradicting"}
        }
        resolved_at = report.observed_at
        current_outcomes: set[str] = set()
        current = relevant.get(report.report_id)
        if current is None:
            return

        for report_id, metadata in relevant.items():
            if report_id == report.report_id or metadata.get("source_id") == report.source_id:
                continue
            resolution_status = (
                "corroborated"
                if metadata["polarity"] == current["polarity"]
                else "contradicted"
            )
            current_outcomes.add(resolution_status)
            source_id = str(metadata.get("source_id", ""))
            source_type = str(metadata.get("source_type", ""))
            if not source_id or not source_type:
                continue
            await self.ensure_source_bank(source_id)
            await self._repository.retain_source_outcome(
                source_id=source_id,
                source_type=source_type,
                vehicle_id=str(metadata.get("vehicle_id", vehicle_id)),
                report_id=report_id,
                triggering_report_id=report.report_id,
                issue_candidate=report.issue_candidate,
                resolution_status=resolution_status,
                resolved_at=resolved_at,
                recorded_at=report.submitted_at or datetime.now(timezone.utc),
            )

        if current_outcomes:
            resolution_status = (
                next(iter(current_outcomes))
                if len(current_outcomes) == 1
                else "unresolved"
            )
            await self.ensure_source_bank(report.source_id)
            await self._repository.retain_source_outcome(
                source_id=report.source_id,
                source_type=report.source_type,
                vehicle_id=vehicle_id,
                report_id=report.report_id,
                triggering_report_id=report.report_id,
                issue_candidate=report.issue_candidate,
                resolution_status=resolution_status,
                resolved_at=resolved_at,
                recorded_at=report.submitted_at or datetime.now(timezone.utc),
            )

    async def recall_vehicle_history(self, vehicle_id: str, query: str) -> list[MemoryEvidence]:
        return await self._repository.recall_vehicle(vehicle_id, query)

    async def recall_source_history(self, source_id: str, query: str) -> list[MemoryEvidence]:
        return await self._repository.recall_source(source_id, query)

    async def explain_assessment_change(self, vehicle_id: str, assessment_context: str) -> str:
        return await self._repository.reflect(vehicle_id, assessment_context)

    async def check_version(self):
        return await self._repository.check_version()

    async def close(self) -> None:
        await self._repository.close()
