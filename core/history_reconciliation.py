from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable

from core.condition import ConditionRecord
from core.models import Car, UNKNOWN
from memory.hindsight import MemoryItem


@dataclass(frozen=True)
class HistoricalSnapshot:
    report_id: str
    observed_at: datetime | None
    vehicle: dict[str, Any]
    condition: ConditionRecord
    metadata: dict[str, Any]


@dataclass(frozen=True)
class HistoryFinding:
    kind: str
    field: str
    current_value: Any
    historical_value: Any
    report_id: str
    message: str


@dataclass(frozen=True)
class InfluentialMemory:
    field: str
    relevance: str
    report_id: str
    observed_at: str
    reason: str
    memory: str
    source_reliability: str
    evidence_confidence: str


@dataclass(frozen=True)
class HistoryReconciliation:
    status: str
    snapshots: tuple[HistoricalSnapshot, ...] = ()
    findings: tuple[HistoryFinding, ...] = ()
    influential_memories: tuple[InfluentialMemory, ...] = ()
    ignored_items: int = 0


def _parse_snapshot(item: MemoryItem) -> HistoricalSnapshot | None:
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
        metadata=item.metadata,
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

def _influential(
    snapshot: HistoricalSnapshot,
    field: str,
    relevance: str,
    reason: str,
) -> InfluentialMemory:
    dt_str = snapshot.observed_at.isoformat() if snapshot.observed_at else "Unknown Date"
    return InfluentialMemory(
        field=field,
        relevance=relevance,
        report_id=snapshot.report_id,
        observed_at=dt_str,
        reason=reason,
        memory=f"Historical report {snapshot.report_id}",
        source_reliability=snapshot.metadata.get("source_reliability", "unverified"),
        evidence_confidence=snapshot.metadata.get("evidence_confidence", "unverified")
    )


def reconcile_vehicle_history(
    car: Car,
    current_condition: ConditionRecord,
    items: list[MemoryItem] | tuple[MemoryItem, ...],
) -> HistoryReconciliation:
    snapshots = [
        snapshot
        for item in items
        if (snapshot := _parse_snapshot(item)) is not None
    ]
    # Chronological sort (oldest to newest)
    snapshots.sort(
        key=lambda snapshot: snapshot.observed_at or datetime.min
    )

    if not snapshots:
        return HistoryReconciliation(
            status="NO_HISTORY",
            ignored_items=len(items),
        )

    findings: list[HistoryFinding] = []
    influential: list[InfluentialMemory] = []
    
    def analyze_field(field_path: str, label: str, current_val: Any,
                      extractor: Callable[[HistoricalSnapshot], Any],
                      is_monotonic: bool = False, is_immutable: bool = False):
        
        history = []
        for s in snapshots:
            val = extractor(s)
            if _known(val):
                history.append((s, val))
        
        if not history:
            return
        
        # Check historical sequence for internal contradictions
        for i in range(1, len(history)):
            prev_s, prev_val = history[i-1]
            curr_s, curr_val = history[i]
            
            if is_monotonic:
                if curr_val < prev_val:
                    influential.append(_influential(curr_s, field_path, "historical contradiction", f"{label} decreased from {prev_val} to {curr_val}"))
                    influential.append(_influential(prev_s, field_path, "historical contradiction", f"Previous higher {label} {prev_val}"))
            elif is_immutable:
                if curr_val != prev_val:
                    influential.append(_influential(curr_s, field_path, "historical contradiction", f"{label} changed from {prev_val} to {curr_val}"))
                    influential.append(_influential(prev_s, field_path, "historical contradiction", f"Previous {label} {prev_val}"))
                    
        # Compare current to history
        latest_s, latest_val = history[-1]
        
        if not _known(current_val):
            return
            
        if current_val == latest_val:
            findings.append(_finding(kind="MATCH", field=field_path, current=current_val, historical=latest_val, snapshot=latest_s, message=f"{label} matches the historical record."))
            influential.append(_influential(latest_s, field_path, "historical baseline", f"Established baseline for {label} matches current."))
        else:
            if is_monotonic:
                if current_val < latest_val:
                    findings.append(_finding(kind="CONTRADICTION", field=field_path, current=current_val, historical=latest_val, snapshot=latest_s, message=f"Current {label.lower()} ({current_val}) is lower than the historical reading ({latest_val})."))
                    influential.append(_influential(latest_s, field_path, "historical contradiction", f"Previous reading ({latest_val}) conflicts with current."))
                else:
                    findings.append(_finding(kind="CHANGED", field=field_path, current=current_val, historical=latest_val, snapshot=latest_s, message=f"{label} increased from {latest_val} to {current_val}."))
            elif is_immutable:
                findings.append(_finding(kind="CONTRADICTION", field=field_path, current=current_val, historical=latest_val, snapshot=latest_s, message=f"{label} conflicts with the historical record: current={current_val!r}, historical={latest_val!r}."))
                influential.append(_influential(latest_s, field_path, "historical contradiction", f"Previous {label} ({latest_val}) conflicts with current."))
            else:
                findings.append(_finding(kind="CHANGED", field=field_path, current=current_val, historical=latest_val, snapshot=latest_s, message=f"{label} changed from {latest_val!r} to {current_val!r}."))
                influential.append(_influential(latest_s, field_path, "historical context", f"Previous {label} was {latest_val}."))

    # vehicle identity
    for f_name, f_label in (("brand", "Brand"), ("model", "Model"), ("manufacture_year", "Manufacture year"), ("vin", "VIN")):
        analyze_field(f_name, f_label, getattr(car, f_name), lambda s, fn=f_name: s.vehicle.get(fn), is_immutable=True)
    
    # odometer
    analyze_field("odometer_km", "Odometer", car.odometer_km, lambda s: s.vehicle.get("odometer_km"), is_monotonic=True)

    # scalar fields
    for f_name, f_label in (("accident_status", "Accident history"), ("airbag_deployed", "Airbag deployment")):
        analyze_field(f_name, f_label, getattr(current_condition, f_name), lambda s, fn=f_name: getattr(s.condition, fn), is_immutable=True)
        
    analyze_field("repainted_panels", "Repaint information", current_condition.repainted_panels, lambda s: s.condition.repainted_panels, is_immutable=False)

    # mappings
    for prefix, current_dict, extractor in (
        ("documents", current_condition.documents, lambda s: s.condition.documents),
        ("physical_inspection", current_condition.physical_inspection, lambda s: s.condition.physical_inspection),
        ("test_drive", current_condition.test_drive, lambda s: s.condition.test_drive),
    ):
        for field, current_value in current_dict.items():
            analyze_field(f"{prefix}.{field}", field, current_value, lambda s, e=extractor, f=field: e(s).get(f, UNKNOWN), is_immutable=False)

    historical_repairs = set()
    for s in snapshots:
        for item in s.condition.repairs:
            historical_repairs.add((item.observed_at.isoformat(), item.odometer_km, item.category, item.description))
            influential.append(_influential(s, "repairs", "historical context", f"Previous repair: {item.description}"))
            
    new_repairs = [item for item in current_condition.repairs if (item.observed_at.isoformat(), item.odometer_km, item.category, item.description) not in historical_repairs]
    if new_repairs and snapshots:
        findings.append(_finding(kind="CHANGED", field="repairs", current=len(current_condition.repairs), historical=len(historical_repairs), snapshot=snapshots[-1], message=f"{len(new_repairs)} current repair record(s) are newer/not present in this history snapshot."))

    historical_services = set()
    for s in snapshots:
        for item in s.condition.services:
            historical_services.add((item.observed_at.isoformat(), item.odometer_km, item.description))
            influential.append(_influential(s, "services", "historical context", f"Previous service: {item.description}"))
            
    new_services = [item for item in current_condition.services if (item.observed_at.isoformat(), item.odometer_km, item.description) not in historical_services]
    if new_services and snapshots:
        findings.append(_finding(kind="CHANGED", field="services", current=len(current_condition.services), historical=len(historical_services), snapshot=snapshots[-1], message=f"{len(new_services)} current service record(s) are newer/not present in this history snapshot."))

    unique_influential = []
    seen_inf = set()
    for inf in influential:
        key = (inf.field, inf.relevance, inf.report_id, inf.reason)
        if key not in seen_inf:
            seen_inf.add(key)
            unique_influential.append(inf)

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
        snapshots=tuple(reversed(snapshots)),
        findings=tuple(findings),
        influential_memories=tuple(unique_influential),
        ignored_items=len(items) - len(snapshots),
    )
