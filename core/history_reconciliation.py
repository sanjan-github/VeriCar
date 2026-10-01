from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from core.condition import ConditionRecord
from core.models import Car, UNKNOWN
from memory.hindsight import MemoryItem


@dataclass(frozen=True)
class HistoricalSnapshot:
    """A structured vehicle evidence snapshot recovered from memory."""

    report_id: str
    observed_at: datetime | None
    vehicle: dict[str, Any]
    condition: ConditionRecord
    metadata: dict[str, Any]


@dataclass(frozen=True)
class HistoryFinding:
    """A deterministic comparison between current and historical evidence."""

    kind: str
    field: str
    current_value: Any
    historical_value: Any
    report_id: str
    message: str


@dataclass(frozen=True)
class HistoryReconciliation:
    """Evidence-only result; it never changes the vehicle assessment."""

    status: str
    snapshots: tuple[HistoricalSnapshot, ...] = ()
    findings: tuple[HistoryFinding, ...] = ()
    ignored_items: int = 0
    longitudinal_findings: tuple[HistoryFinding, ...] = ()


def _parse_snapshot(item: MemoryItem) -> HistoricalSnapshot | None:
    """Extract the JSON snapshot written by build_vehicle_memory_report."""
    marker = "VeriCar vehicle evidence report."
    if marker not in item.text:
        return None

    start = item.text.find("{")
    if start < 0:
        return None

    try:
        payload, _ = json.JSONDecoder().raw_decode(item.text[start:])
        vehicle = payload["vehicle"]
        condition = ConditionRecord.from_record(payload["condition"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    observed_at: datetime | None = None
    raw_observed_at = item.metadata.get("observed_at")
    if isinstance(raw_observed_at, str):
        try:
            observed_at = datetime.fromisoformat(raw_observed_at)
        except ValueError:
            observed_at = None

    report_id = str(
        item.metadata.get("report_id")
        or vehicle.get("report_id")
        or item.memory_id
    )
    return HistoricalSnapshot(
        report_id=report_id,
        observed_at=observed_at,
        vehicle=vehicle,
        condition=condition,
        metadata=dict(item.metadata),
    )


def _known(value: Any) -> bool:
    return value is not None and value != UNKNOWN and value != ""


def _finding(
    *,
    kind: str,
    field: str,
    current: Any,
    historical: Any,
    snapshot: HistoricalSnapshot,
    message: str,
) -> HistoryFinding:
    return HistoryFinding(
        kind=kind,
        field=field,
        current_value=current,
        historical_value=historical,
        report_id=snapshot.report_id,
        message=message,
    )


def _compare_scalar_fields(
    current: ConditionRecord,
    historical: ConditionRecord,
    snapshot: HistoricalSnapshot,
) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []

    # These represent historical facts that should not silently reverse.
    immutable_history = (
        ("accident_status", "Accident history"),
        ("airbag_deployed", "Airbag deployment"),
    )
    for field, label in immutable_history:
        current_value = getattr(current, field)
        historical_value = getattr(historical, field)
        if _known(current_value) and _known(historical_value):
            if current_value == historical_value:
                findings.append(
                    _finding(
                        kind="MATCH",
                        field=field,
                        current=current_value,
                        historical=historical_value,
                        snapshot=snapshot,
                        message=f"{label} matches the historical record.",
                    )
                )
            else:
                findings.append(
                    _finding(
                        kind="CONTRADICTION",
                        field=field,
                        current=current_value,
                        historical=historical_value,
                        snapshot=snapshot,
                        message=(
                            f"{label} conflicts with the historical record: "
                            f"current={current_value!r}, historical={historical_value!r}."
                        ),
                    )
                )

    current_repaint = current.repainted_panels
    historical_repaint = historical.repainted_panels
    if _known(current_repaint) and _known(historical_repaint):
        if current_repaint == historical_repaint:
            findings.append(
                _finding(
                    kind="MATCH",
                    field="repainted_panels",
                    current=current_repaint,
                    historical=historical_repaint,
                    snapshot=snapshot,
                    message="Repaint information matches the historical record.",
                )
            )
        else:
            findings.append(
                _finding(
                    kind="CHANGED",
                    field="repainted_panels",
                    current=current_repaint,
                    historical=historical_repaint,
                    snapshot=snapshot,
                    message=(
                        "Repaint information has changed since the historical record."
                    ),
                )
            )

    return findings


def _compare_odometer(
    current_car: Car,
    historical_car: dict[str, Any],
    snapshot: HistoricalSnapshot,
) -> list[HistoryFinding]:
    current = current_car.odometer_km
    historical = historical_car.get("odometer_km")
    if current is None or historical is None:
        return []

    if current > historical:
        return [
            _finding(
                kind="CHANGED",
                field="odometer_km",
                current=current,
                historical=historical,
                snapshot=snapshot,
                message=f"Odometer increased from {historical:,} km to {current:,} km.",
            )
        ]
    if current == historical:
        return [
            _finding(
                kind="MATCH",
                field="odometer_km",
                current=current,
                historical=historical,
                snapshot=snapshot,
                message=f"Odometer matches the historical record at {current:,} km.",
            )
        ]
    return [
        _finding(
            kind="CONTRADICTION",
            field="odometer_km",
            current=current,
            historical=historical,
            snapshot=snapshot,
            message=(
                f"Current odometer ({current:,} km) is lower than the "
                f"historical reading ({historical:,} km)."
            ),
        )
    ]


def _compare_mapping(
    current: dict[str, str],
    historical: dict[str, str],
    snapshot: HistoricalSnapshot,
    *,
    prefix: str,
) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []
    for field, current_value in current.items():
        historical_value = historical.get(field, UNKNOWN)
        if not (_known(current_value) and _known(historical_value)):
            continue
        if current_value == historical_value:
            findings.append(
                _finding(
                    kind="MATCH",
                    field=f"{prefix}.{field}",
                    current=current_value,
                    historical=historical_value,
                    snapshot=snapshot,
                    message=f"{field} matches the historical record.",
                )
            )
        else:
            findings.append(
                _finding(
                    kind="CHANGED",
                    field=f"{prefix}.{field}",
                    current=current_value,
                    historical=historical_value,
                    snapshot=snapshot,
                    message=f"{field} changed from {historical_value!r} to {current_value!r}.",
                )
            )
    return findings


def _compare_vehicle_identity(
    current_car: Car,
    historical_vehicle: dict[str, Any],
    snapshot: HistoricalSnapshot,
) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []
    for field, label in (
        ("brand", "Brand"),
        ("model", "Model"),
        ("manufacture_year", "Manufacture year"),
        ("vin", "VIN"),
    ):
        current_value = getattr(current_car, field)
        historical_value = historical_vehicle.get(field)
        if not (_known(current_value) and _known(historical_value)):
            continue
        if str(current_value).strip() != str(historical_value).strip():
            findings.append(
                _finding(
                    kind="CONTRADICTION",
                    field=field,
                    current=current_value,
                    historical=historical_value,
                    snapshot=snapshot,
                    message=(
                        f"{label} conflicts with the historical record: "
                        f"current={current_value!r}, historical={historical_value!r}."
                    ),
                )
            )
    return findings


def _compare_repairs_and_services(
    current: ConditionRecord,
    historical: ConditionRecord,
    snapshot: HistoricalSnapshot,
) -> list[HistoryFinding]:
    findings: list[HistoryFinding] = []

    historical_repairs = {
        (
            item.observed_at.isoformat(),
            item.odometer_km,
            item.category,
            item.description,
        )
        for item in historical.repairs
    }
    new_repairs = [
        item
        for item in current.repairs
        if (
            item.observed_at.isoformat(),
            item.odometer_km,
            item.category,
            item.description,
        )
        not in historical_repairs
    ]
    if new_repairs:
        findings.append(
            _finding(
                kind="CHANGED",
                field="repairs",
                current=len(current.repairs),
                historical=len(historical.repairs),
                snapshot=snapshot,
                message=f"{len(new_repairs)} current repair record(s) are newer/not present in this history snapshot.",
            )
        )

    historical_services = {
        (
            item.observed_at.isoformat(),
            item.odometer_km,
            item.description,
        )
        for item in historical.services
    }
    new_services = [
        item
        for item in current.services
        if (
            item.observed_at.isoformat(),
            item.odometer_km,
            item.description,
        )
        not in historical_services
    ]
    if new_services:
        findings.append(
            _finding(
                kind="CHANGED",
                field="services",
                current=len(current.services),
                historical=len(historical.services),
                snapshot=snapshot,
                message=f"{len(new_services)} current service record(s) are newer/not present in this history snapshot.",
            )
        )

    return findings


def _compare_longitudinal_snapshots(
    snapshots: list[HistoricalSnapshot],
) -> list[HistoryFinding]:
    """Compare adjacent historical observations to expose multi-report changes."""
    findings: list[HistoryFinding] = []
    ordered = sorted(snapshots, key=lambda snapshot: snapshot.observed_at or datetime.min)
    for previous, current in zip(ordered, ordered[1:]):
        previous_odometer = previous.vehicle.get("odometer_km")
        current_odometer = current.vehicle.get("odometer_km")
        if previous_odometer is not None and current_odometer is not None and current_odometer < previous_odometer:
            findings.append(HistoryFinding(
                kind="CONTRADICTION", field="odometer_km",
                current_value=current_odometer, historical_value=previous_odometer,
                report_id=current.report_id,
                message=f'Historical odometer sequence regressed from {previous_odometer:,} km to {current_odometer:,} km.',
            ))
        for field, label in (
            ("accident_status", "Accident history"),
            ("airbag_deployed", "Airbag deployment"),
            ("repainted_panels", "Repaint information"),
        ):
            previous_value = getattr(previous.condition, field)
            current_value = getattr(current.condition, field)
            if not (_known(previous_value) and _known(current_value)) or previous_value == current_value:
                continue
            kind = "CONTRADICTION" if field in {"accident_status", "airbag_deployed"} else "CHANGED"
            findings.append(HistoryFinding(
                kind=kind, field=field, current_value=current_value,
                historical_value=previous_value, report_id=current.report_id,
                message=f'{label} changed between historical reports: {previous_value!r} -> {current_value!r}.',
            ))
    return findings

def reconcile_vehicle_history(
    car: Car,
    current_condition: ConditionRecord,
    items: list[MemoryItem] | tuple[MemoryItem, ...],
) -> HistoryReconciliation:
    """Compare current evidence with structured historical reports.

    Only reports produced by VeriCar's evidence snapshot format are used.
    Recalled memory is treated as evidence, not as authority.
    """
    snapshots = [
        snapshot
        for item in items
        if (snapshot := _parse_snapshot(item)) is not None
    ]
    snapshots.sort(
        key=lambda snapshot: snapshot.observed_at
        or datetime.min,
        reverse=True,
    )

    if not snapshots:
        return HistoryReconciliation(
            status="NO_HISTORY",
            ignored_items=len(items),
        )

    latest = snapshots[0]
    findings: list[HistoryFinding] = []
    longitudinal_findings = _compare_longitudinal_snapshots(snapshots)
    findings.extend(_compare_vehicle_identity(car, latest.vehicle, latest))
    findings.extend(_compare_odometer(car, latest.vehicle, latest))
    findings.extend(
        _compare_scalar_fields(current_condition, latest.condition, latest)
    )
    findings.extend(
        _compare_mapping(
            current_condition.documents,
            latest.condition.documents,
            latest,
            prefix="documents",
        )
    )
    findings.extend(
        _compare_mapping(
            current_condition.physical_inspection,
            latest.condition.physical_inspection,
            latest,
            prefix="physical_inspection",
        )
    )
    findings.extend(
        _compare_mapping(
            current_condition.test_drive,
            latest.condition.test_drive,
            latest,
            prefix="test_drive",
        )
    )
    findings.extend(
        _compare_repairs_and_services(current_condition, latest.condition, latest)
    )

    kinds = {finding.kind for finding in findings}
    if "CONTRADICTION" in kinds:
        status = "CONTRADICTION"
    elif "CHANGED" in kinds:
        status = "CHANGED"
    elif "MATCH" in kinds:
        status = "MATCHED"
    else:
        status = "INSUFFICIENT"

    return HistoryReconciliation(
        status=status,
        snapshots=tuple(snapshots),
        findings=tuple(findings),
        ignored_items=len(items) - len(snapshots),
        longitudinal_findings=tuple(longitudinal_findings),
    )
