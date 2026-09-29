from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from core.database import Database
from core.memory_report import build_vehicle_memory_report
from core.models import Car
from core.condition import ConditionRecord
from memory.hindsight import HindsightMemory


def sync_condition_to_memory(car: Car, condition: ConditionRecord, db: Database) -> tuple[str, str | None]:
    report = build_vehicle_memory_report(car, condition)
    db.record_memory_report(
        report_id=report.report_id, car_id=car.car_id,
        observed_at=report.observed_at.isoformat(), status="pending",
    )
    try:
        asyncio.run(
            HindsightMemory().retain_vehicle_report(
                vehicle_id=report.vehicle_id, report_id=report.report_id,
                text=report.text, observed_at=report.observed_at,
                metadata=report.metadata,
            )
        )
        db.record_memory_report(
            report_id=report.report_id, car_id=car.car_id,
            observed_at=report.observed_at.isoformat(), status="synced",
            synced_at=datetime.now(timezone.utc).isoformat(),
        )
        return report.report_id, None
    except Exception as exc:
        db.record_memory_report(
            report_id=report.report_id, car_id=car.car_id,
            observed_at=report.observed_at.isoformat(), status="failed",
            error=str(exc)[:500],
        )
        return report.report_id, str(exc)
