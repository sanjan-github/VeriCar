from __future__ import annotations

import asyncio
from dataclasses import dataclass
import re
from difflib import SequenceMatcher

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


_DATE_MARKER_RE = re.compile(
    r"\\s*(?:\\|\\s*)?(?:when|on|as of)\\s*:?\\s*\\d{4}-\\d{2}-\\d{2}\\b",
    re.IGNORECASE,
)


def _memory_display_key(text: str) -> str:
    """Normalize cosmetic wording so repeated Hindsight observations collapse."""
    value = _DATE_MARKER_RE.sub("", text)
    value = re.sub(r"\\s+", " ", value).strip().lower()
    value = re.sub(r"^[\\s,.;:!-]*(?:the|a|an)\\s+", "", value)
    return value


def _dedupe_memory_items(items: list[MemoryItem]) -> tuple[MemoryItem, ...]:
    """Return distinct human-readable memory notes without altering history data."""
    unique: list[MemoryItem] = []
    keys: list[str] = []

    for item in items:
        key = _memory_display_key(item.text)
        if not key:
            continue
        duplicate = any(
            key == existing
            or SequenceMatcher(None, key, existing).ratio() >= 0.92
            for existing in keys
        )
        if duplicate:
            continue
        keys.append(key)
        unique.append(item)

    return tuple(unique)


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
        items=_dedupe_memory_items(items),
    )



def recall_vehicle_history(
    car: Car,
    *,
    query: str = "vehicle evidence report",
) -> MemoryRecallResult:
    """Recall original retained reports for deterministic history reconciliation."""

    if not query.strip():
        raise ValueError("query must not be empty.")

    try:
        items = asyncio.run(
            HindsightMemory().recall_vehicle_reports(
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
