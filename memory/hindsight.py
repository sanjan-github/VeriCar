from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from dotenv import load_dotenv
from hindsight_client import Hindsight

from core.config import env_float, env_url

load_dotenv()


class HindsightClient(Protocol):
    async def acreate_bank(self, *, bank_id: str, name: str, mission: str) -> Any: ...
    async def aretain(self, **kwargs: Any) -> Any: ...
    async def arecall(self, **kwargs: Any) -> Any: ...
    async def aclose(self) -> Any: ...


@dataclass(frozen=True)
class MemoryItem:
    """Normalized memory returned to the application."""

    memory_id: str
    text: str
    metadata: dict[str, Any]
    tags: list[str]


VEHICLE_MISSION = (
    "Maintain an evidence-grounded history of one vehicle. "
    "Preserve reports across time and contradictory observations. "
    "Never treat one report as established mechanical truth."
)


class HindsightMemory:
    """Small application adapter around the verified Hindsight client API.

    The adapter deliberately exposes only the memory operations VeriCar needs
    at this stage. Rules, scoring, and LLM reasoning remain outside this layer.
    """

    def __init__(self, client: HindsightClient | None = None) -> None:
        self._client = client or self._build_client()

    @staticmethod
    def _build_client() -> HindsightClient:
        base_url = env_url("HINDSIGHT_BASE_URL", "http://localhost:8888")
        api_key = os.getenv("HINDSIGHT_API_KEY") or None
        timeout = env_float("HINDSIGHT_TIMEOUT", 30.0)
        return Hindsight(
            base_url=base_url,
            api_key=api_key,
            timeout=timeout,
        )

    @staticmethod
    def _bank_id(vehicle_id: str) -> str:
        vehicle_id = vehicle_id.strip()
        if not vehicle_id:
            raise ValueError("vehicle_id must not be empty.")
        return f"vehicle_{vehicle_id}"

    async def ensure_vehicle(self, vehicle_id: str) -> None:
        bank_id = self._bank_id(vehicle_id)
        await self._client.acreate_bank(
            bank_id=bank_id,
            name=f"Vehicle history {vehicle_id.strip()}",
            mission=VEHICLE_MISSION,
        )

    async def retain_vehicle_report(
        self,
        *,
        vehicle_id: str,
        report_id: str,
        text: str,
        observed_at: datetime,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Persist one historical vehicle report with stable identifiers."""

        if not text.strip():
            raise ValueError("report text must not be empty.")
        if not report_id.strip():
            raise ValueError("report_id must not be empty.")

        await self.ensure_vehicle(vehicle_id)

        report_metadata = dict(metadata or {})
        report_metadata.update(
            {
                "vehicle_id": vehicle_id.strip(),
                "report_id": report_id.strip(),
                "observed_at": observed_at.isoformat(),
            }
        )

        tags = ["vehicle", f"vehicle:{vehicle_id.strip()}"]
        source_id = report_metadata.get("source_id")
        if source_id:
            tags.append(f"source:{source_id}")

        return await self._client.aretain(
            bank_id=self._bank_id(vehicle_id),
            content=text.strip(),
            context="vehicle history report",
            timestamp=observed_at,
            document_id=f"report_{report_id.strip()}",
            metadata=report_metadata,
            tags=tags,
            retain_async=False,
        )

    async def recall_vehicle(
        self,
        *,
        vehicle_id: str,
        query: str,
    ) -> list[MemoryItem]:
        """Recall semantic historical evidence for the vehicle UI."""

        return await self._recall(
            vehicle_id=vehicle_id,
            query=query,
            types=["world", "experience", "observation"],
            prefer_observations=True,
            include_source_facts=True,
        )

    async def recall_vehicle_reports(
        self,
        *,
        vehicle_id: str,
        query: str = "vehicle evidence report",
    ) -> list[MemoryItem]:
        """Recall original retained reports for deterministic reconciliation."""

        return await self._recall(
            vehicle_id=vehicle_id,
            query=query,
            types=["world"],
            prefer_observations=False,
            include_source_facts=True,
        )

    async def _recall(
        self,
        *,
        vehicle_id: str,
        query: str,
        types: list[str],
        prefer_observations: bool,
        include_source_facts: bool,
    ) -> list[MemoryItem]:
        if not query.strip():
            raise ValueError("query must not be empty.")

        response = await self._client.arecall(
            bank_id=self._bank_id(vehicle_id),
            query=query.strip(),
            types=types,
            budget="mid",
            max_tokens=4096,
            include_source_facts=include_source_facts,
            prefer_observations=prefer_observations,
            tags=[f"vehicle:{vehicle_id.strip()}"],
        )

        items = getattr(response, "results", None)
        if items is None and isinstance(response, dict):
            items = response.get("results")
        if items is None:
            items = response if isinstance(response, list) else []

        normalized: list[MemoryItem] = []
        for item in items:
            if isinstance(item, dict):
                value = item
            else:
                value = {
                    "id": getattr(item, "id", ""),
                    "text": getattr(item, "text", ""),
                    "metadata": getattr(item, "metadata", None),
                    "tags": getattr(item, "tags", None),
                }

            normalized.append(
                MemoryItem(
                    memory_id=str(value.get("id", "")),
                    text=str(value.get("text", "")),
                    metadata=value.get("metadata") or {},
                    tags=list(value.get("tags") or []),
                )
            )

        return normalized

    async def close(self) -> None:
        await self._client.aclose()
