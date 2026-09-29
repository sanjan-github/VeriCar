from __future__ import annotations

import asyncio
from dataclasses import dataclass

from core.models import Car
from memory.hindsight import HindsightMemory, MemoryItem


@dataclass(frozen=True)
class MemoryRecallResult:
    """Result of a vehicle-memory lookup.

    status is either AVAILABLE or UNAVAILABLE. An unavailable memory service
    must never be presented as an empty vehicle history.
    """

    status: str
    items: tuple[MemoryItem, ...] = ()
    error: str | None = None


def recall_vehicle_memory(
    car: Car,
    *,
    query: str,
) -> MemoryRecallResult:
    """Recall historical evidence for a vehicle without affecting assessment."""

    if not query.strip():
        raise ValueError("query must not be empty.")

    try:
        items = asyncio.run(
            HindsightMemory().recall_vehicle(
                vehicle_id=car.car_id,
                query=query,
            )
        )
    except Exception as exc:
        return MemoryRecallResult(
            status="UNAVAILABLE",
            error=str(exc)[:500],
        )

    return MemoryRecallResult(
        status="AVAILABLE",
        items=tuple(items),
    )
