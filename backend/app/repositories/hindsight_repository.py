from __future__ import annotations

from dataclasses import asdict
from typing import Any, Protocol

from backend.app.models.memory import MemoryEvidence, VehicleReport


class HindsightClientProtocol(Protocol):
    async def acreate_bank(self, *, bank_id: str, name: str, mission: str) -> Any: ...
    async def aretain(self, **kwargs: Any) -> Any: ...
    async def arecall(self, **kwargs: Any) -> Any: ...
    async def areflect(self, **kwargs: Any) -> Any: ...
    async def aget_version(self) -> Any: ...
    async def aclose(self) -> Any: ...


class HindsightRepository:
    """Thin adapter around the Hindsight Python client."""

    def __init__(self, client: HindsightClientProtocol) -> None:
        self._client = client

    async def check_version(self) -> Any:
        return await self._client.aget_version()

    async def ensure_bank(self, bank_id: str, name: str, mission: str) -> None:
        await self._client.acreate_bank(
            bank_id=bank_id,
            name=name,
            mission=mission,
        )

    async def retain_report(self, report: VehicleReport) -> Any:
        return await self._client.aretain(
            bank_id=f"vehicle_{report.vin}",
            content=report.text,
            context="vehicle history report",
            timestamp=report.observed_at,
            document_id=f"report_{report.report_id}",
            metadata={
                "vehicle_id": report.vehicle_id or report.vin,
                "vin": report.vin,
                "source_id": report.source_id,
                "source_type": report.source_type,
                "report_id": report.report_id,
                "observed_at": report.observed_at.isoformat(),
                "submitted_at": (
                    report.submitted_at.isoformat()
                    if report.submitted_at is not None
                    else None
                ),
            },
            tags=["vehicle", f"vin:{report.vin}", f"source:{report.source_id}"],
            retain_async=False,
        )

    async def retain_source_report(self, report: VehicleReport) -> Any:
        return await self._client.aretain(
            bank_id=f"source_{report.source_id}",
            content=report.text,
            context="historical source report",
            timestamp=report.observed_at,
            document_id=f"report_{report.report_id}",
            metadata={
                "vin": report.vin,
                "source_id": report.source_id,
                "source_type": report.source_type,
                "report_id": report.report_id,
            },
            tags=["source", f"source:{report.source_id}", f"vin:{report.vin}"],
            retain_async=False,
        )

    async def recall_vehicle(self, vin: str, query: str) -> list[MemoryEvidence]:
        response = await self._client.arecall(
            bank_id=f"vehicle_{vin}",
            query=query,
            types=["world", "experience", "observation"],
            budget="mid",
            max_tokens=4096,
            include_source_facts=True,
            prefer_observations=True,
            tags=[f"vin:{vin}"],
        )
        return self._normalize_recall(response)

    async def recall_source(self, source_id: str, query: str) -> list[MemoryEvidence]:
        response = await self._client.arecall(
            bank_id=f"source_{source_id}",
            query=query,
            types=["world", "experience", "observation"],
            budget="mid",
            max_tokens=4096,
            include_source_facts=True,
            prefer_observations=True,
            tags=[f"source:{source_id}"],
        )
        return self._normalize_recall(response)

    async def reflect(self, vin: str, assessment_context: str) -> str:
        response = await self._client.areflect(
            bank_id=f"vehicle_{vin}",
            query=(
                "Assess the accumulated evidence for the current vehicle finding. "
                "Explain what changed compared with earlier reports."
            ),
            budget="low",
            context=assessment_context,
            include_facts=True,
        )
        return self._extract_text(response)

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _normalize_recall(response: Any) -> list[MemoryEvidence]:
        items = getattr(response, "results", None)
        if items is None and isinstance(response, dict):
            items = response.get("results")
        if items is None:
            items = response if isinstance(response, list) else []

        normalized: list[MemoryEvidence] = []
        for item in items:
            value = asdict(item) if hasattr(item, "__dataclass_fields__") else item
            if not isinstance(value, dict):
                value = {
                    name: getattr(item, name, None)
                    for name in (
                        "id", "text", "type", "context", "metadata", "tags",
                        "occurred_start", "occurred_end", "mentioned_at",
                        "document_id", "chunk_id",
                    )
                }
            normalized.append(
                MemoryEvidence(
                    memory_id=str(value.get("id", "")),
                    text=str(value.get("text", "")),
                    memory_type=value.get("type"),
                    context=value.get("context"),
                    metadata=value.get("metadata") or {},
                    tags=value.get("tags") or [],
                    occurred_start=value.get("occurred_start"),
                    occurred_end=value.get("occurred_end"),
                    mentioned_at=value.get("mentioned_at"),
                    document_id=value.get("document_id"),
                    chunk_id=value.get("chunk_id"),
                )
            )
        return normalized

    @staticmethod
    def _extract_text(response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            return str(response.get("text", ""))
        return str(getattr(response, "text", ""))
