import sqlite3

import pytest

from core.condition import ConditionRecord
from core.database import Database
from core.models import Car


def make_car(car_id="CAR-DB"):
    return Car(car_id=car_id, brand="Toyota", model="City", manufacture_year=2020)


def test_save_car_is_idempotent_and_updates_existing_record(tmp_path):
    db = Database(tmp_path / "vericar.db")
    first = make_car()
    db.save_car(first)

    updated = make_car()
    updated.odometer_km = 85000
    db.save_car(updated)

    row = db.get_car("CAR-DB")
    assert row["odometer_km"] == 85000
    assert len(db.list_cars()) == 1


def test_foreign_keys_prevent_orphan_condition_records(tmp_path):
    db = Database(tmp_path / "vericar.db")
    condition = ConditionRecord.empty("MISSING-CAR")

    with pytest.raises(sqlite3.IntegrityError):
        db.save_condition(condition)


def test_list_cars_rejects_non_positive_limits(tmp_path):
    db = Database(tmp_path / "vericar.db")
    with pytest.raises(ValueError, match="positive integer"):
        db.list_cars(0)
    with pytest.raises(ValueError, match="positive integer"):
        db.list_cars(-1)


def test_memory_report_status_can_retry_after_failure(tmp_path):
    db = Database(tmp_path / "vericar.db")
    db.save_car(make_car())

    db.record_memory_report(
        report_id="RPT-1",
        car_id="CAR-DB",
        observed_at="2026-09-30T10:00:00+00:00",
        status="failed",
        error="RuntimeError: Hindsight service unavailable.",
    )
    db.record_memory_report(
        report_id="RPT-1",
        car_id="CAR-DB",
        observed_at="2026-09-30T10:00:00+00:00",
        status="synced",
        synced_at="2026-09-30T10:01:00+00:00",
    )

    row = db.get_memory_report("RPT-1")
    assert row["status"] == "synced"
    assert row["error"] is None
    assert row["synced_at"] == "2026-09-30T10:01:00+00:00"


def test_idempotency_records_lifecycle(tmp_path):
    db = Database(tmp_path / "vericar.db")

    # Initial create returns True
    created = db.create_idempotency_record(
        idempotency_key="key-db-1",
        request_fingerprint="fp-123",
        report_id="RPT-DB-1",
        status="PROCESSING",
    )
    assert created is True

    # Duplicate create with same idempotency_key returns False
    duplicate = db.create_idempotency_record(
        idempotency_key="key-db-1",
        request_fingerprint="fp-123",
        report_id="RPT-DB-DUPLICATE",
        status="PROCESSING",
    )
    assert duplicate is False

    # Retrieve by idempotency_key
    row = db.get_idempotency_record(idempotency_key="key-db-1")
    assert row is not None
    assert row["report_id"] == "RPT-DB-1"
    assert row["status"] == "PROCESSING"
    assert row["vehicle_memory_status"] == "PENDING"

    # Update statuses
    db.update_idempotency_record(
        "RPT-DB-1",
        status="PARTIAL",
        vehicle_memory_status="STORED",
        source_memory_status="FAILED",
    )
    row = db.get_idempotency_record(report_id="RPT-DB-1")
    assert row["status"] == "PARTIAL"
    assert row["vehicle_memory_status"] == "STORED"
    assert row["source_memory_status"] == "FAILED"

    # Update to COMPLETED with response payload
    db.update_idempotency_record(
        "RPT-DB-1",
        status="COMPLETED",
        source_memory_status="STORED",
        resolution_status="STORED",
        response_payload='{"status": "complete"}',
    )
    row = db.get_idempotency_record(idempotency_key="key-db-1")
    assert row["status"] == "COMPLETED"
    assert row["response_payload"] == '{"status": "complete"}'


def test_idempotency_get_record_requires_argument(tmp_path):
    db = Database(tmp_path / "vericar.db")
    with pytest.raises(ValueError, match="Either idempotency_key or report_id"):
        db.get_idempotency_record()

