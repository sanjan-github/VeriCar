from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable

from core.condition import ConditionRecord
from core.models import Car, UNKNOWN
from core.history_reconciliation import HistoryReconciliation, HistoricalSnapshot, HistoryFinding


@dataclass(frozen=True)
class InfluentialMemory:
    """A historical memory selected because it is relevant to current evidence."""

    report_id: str
    observed_at: datetime | None
    field: str
    reason: str
    source_type: str


@dataclass(frozen=True)
class ModelObservation:
    """An observational pattern; never an authoritative model specification."""

    model_key: str
    pattern: str
    count: int
    source_report_ids: tuple[str, ...]


@dataclass(frozen=True)
class LongitudinalMemoryAnalysis:
    """Derived historical context that remains separate from assessment."""

    influential_memories: tuple[InfluentialMemory, ...] = ()
    model_observations: tuple[ModelObservation, ...] = ()


def _known(value: Any) -> bool:
    return value is not None and value != UNKNOWN and value != ""


def _source_type(snapshot: HistoricalSnapshot) -> str:
    value = snapshot.metadata.get("source_type", "unknown")
    return str(value)


def select_influential_memories(
    reconciliation: HistoryReconciliation,
    *,
    limit: int = 8,
) -> tuple[InfluentialMemory, ...]:
    """Select memories tied to meaningful historical findings.

    This is evidence retrieval/selection only. It does not change assessment.
    """
    by_report: dict[str, HistoricalSnapshot] = {
        snapshot.report_id: snapshot for snapshot in reconciliation.snapshots
    }
    selected: list[InfluentialMemory] = []
    seen: set[tuple[str, str]] = set()

    for finding in reconciliation.findings:
        if finding.kind not in {"CONTRADICTION", "CHANGED"}:
            continue
        key = (finding.report_id, finding.field)
        if key in seen or finding.report_id not in by_report:
            continue
        seen.add(key)
        snapshot = by_report[finding.report_id]
        selected.append(
            InfluentialMemory(
                report_id=finding.report_id,
                observed_at=snapshot.observed_at,
                field=finding.field,
                reason=finding.message,
                source_type=_source_type(snapshot),
            )
        )
        if len(selected) >= limit:
            break

    return tuple(selected)


def derive_model_observations(
    snapshots: Iterable[HistoricalSnapshot],
    *,
    limit: int = 10,
) -> tuple[ModelObservation, ...]:
    """Derive repeated observational patterns without changing reference data.

    Only repeated repair categories are surfaced. These observations are
    explicitly non-authoritative and must not mutate expected profiles.
    """
    ordered = list(snapshots)
    if not ordered:
        return ()

    model_key = f"{ordered[0].vehicle.get('brand', '')}:{ordered[0].vehicle.get('model', '')}:{ordered[0].vehicle.get('manufacture_year', '')}"
    reports_by_category: dict[str, list[str]] = {}

    for snapshot in ordered:
        for repair in snapshot.condition.repairs:
            category = str(repair.category).strip()
            if not category:
                continue
            reports_by_category.setdefault(category, []).append(snapshot.report_id)

    observations: list[ModelObservation] = []
    for category, report_ids in sorted(reports_by_category.items()):
        unique_reports = tuple(dict.fromkeys(report_ids))
        if len(unique_reports) < 2:
            continue
        observations.append(
            ModelObservation(
                model_key=model_key,
                pattern=f"Repair category '{category}' was observed across multiple historical reports.",
                count=len(unique_reports),
                source_report_ids=unique_reports,
            )
        )
        if len(observations) >= limit:
            break

    return tuple(observations)


def analyze_longitudinal_memory(
    car: Car,
    condition: ConditionRecord,
    reconciliation: HistoryReconciliation,
) -> LongitudinalMemoryAnalysis:
    """Build useful historical context without modifying deterministic assessment."""
    del car, condition
    return LongitudinalMemoryAnalysis(
        influential_memories=select_influential_memories(reconciliation),
        model_observations=derive_model_observations(reconciliation.snapshots),
    )
