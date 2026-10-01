from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from core.condition import ConditionRecord
from core.models import Car


@dataclass(frozen=True)
class VehicleMemoryReport:
    report_id: str
    vehicle_id: str
    observed_at: datetime
    text: str
    metadata: dict[str, object]


def build_vehicle_memory_report(
    car: Car, condition: ConditionRecord, *, observed_at: datetime | None = None
) -> VehicleMemoryReport:
    """Create an evidence-only snapshot for long-term vehicle memory."""
    timestamp = observed_at or datetime.now(timezone.utc)
    report_id = f"RPT-{uuid4().hex[:12].upper()}"
    payload = {
        "vehicle": {
            "vehicle_id": car.car_id,
            "memory_key": car.memory_key,
            "brand": car.brand,
            "model": car.model,
            "manufacture_year": car.manufacture_year,
            "variant": car.variant,
            "fuel_type": car.fuel_type,
            "transmission": car.transmission,
            "vin": car.vin,
            "registration_state": car.registration_state,
            "odometer_km": car.odometer_km,
            "asking_price_inr": car.asking_price_inr,
        },
        "condition": condition.to_record(),
    }
    text = (
        "VeriCar vehicle evidence report. "
        "This is an observed/input snapshot, not a diagnosis or verdict. "
        "Unknown values remain unknown.\n"
        + json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
    )
    metadata: dict[str, object] = {
        "vehicle_id": car.car_id,
        "memory_key": car.memory_key,
        "report_id": report_id,
        "source_id": "vericar-ui",
        "source_type": "user_entered_evidence",
        "source_reliability": "unverified",
        "evidence_confidence": "unverified",
        "provenance": "vericar-ui",
        "report_kind": "condition_snapshot",
    }
    return VehicleMemoryReport(
        report_id=report_id, vehicle_id=car.car_id, observed_at=timestamp,
        text=text, metadata=metadata,
    )
