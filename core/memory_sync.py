from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from core.condition import ConditionRecord
from core.database import Database
from core.memory_report import build_vehicle_memory_report
from core.models import Car
from memory.hindsight import HindsightMemory

logger = logging.getLogger(__name__)


def _safe_error(exc: Exception) -> str:
    return f"{type(exc).__name__}: Hindsight service unavailable."


def sync_condition_to_memory(car: Car, condition: ConditionRecord, db: Database) -> tuple[str, str | None]:
    report = build_vehicle_memory_report(car, condition)
    existing = db.get_memory_report(report.report_id)
    if existing is not None and existing["status"] == "synced":
        logger.info("Hindsight retention skipped operation=duplicate report_id=%s", report.report_id)
        return report.report_id, None

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
        logger.info("Hindsight retention succeeded operation=retain report_id=%s", report.report_id)
        return report.report_id, None
    except Exception as exc:
        safe_error = _safe_error(exc)
        db.record_memory_report(
            report_id=report.report_id, car_id=car.car_id,
            observed_at=report.observed_at.isoformat(), status="failed",
            error=safe_error,
        )
        logger.warning(
            "Hindsight retention failed operation=retain report_id=%s error_type=%s",
            report.report_id, type(exc).__name__,
        )
        return report.report_id, safe_error
