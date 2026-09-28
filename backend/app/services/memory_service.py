from __future__ import annotations

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

    async def ensure_vehicle_bank(self, vin: str) -> None:
        await self._repository.ensure_bank(
            bank_id=f"vehicle_{vin}",
            name=f"Vehicle history {vin}",
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
        await self.ensure_vehicle_bank(report.vin)
        return await self._repository.retain_report(report)

    async def retain_source_report(self, report: VehicleReport):
        await self.ensure_source_bank(report.source_id)
        return await self._repository.retain_source_report(report)

    async def recall_vehicle_history(self, vin: str, query: str) -> list[MemoryEvidence]:
        return await self._repository.recall_vehicle(vin, query)

    async def recall_source_history(self, source_id: str, query: str) -> list[MemoryEvidence]:
        return await self._repository.recall_source(source_id, query)

    async def explain_assessment_change(self, vin: str, assessment_context: str) -> str:
        return await self._repository.reflect(vin, assessment_context)

    async def check_version(self):
        return await self._repository.check_version()

    async def close(self) -> None:
        await self._repository.close()
