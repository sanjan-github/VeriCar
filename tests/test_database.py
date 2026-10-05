import sqlite3
from contextlib import closing

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


def test_partial_idempotency_retry_can_only_be_claimed_once(tmp_path):
    db = Database(tmp_path / "vericar.db")
    assert db.create_idempotency_record(
        idempotency_key="retry-race",
        request_fingerprint="fingerprint",
        report_id="RPT-RETRY-RACE",
        status="PARTIAL",
        processing_started_at="2026-10-01T00:00:00+00:00",
    )

    first_claim = db.claim_idempotency_retry(
        idempotency_key="retry-race",
        request_fingerprint="fingerprint",
        expected_status="PARTIAL",
        processing_started_at="2026-10-02T00:00:00+00:00",
    )
    competing_claim = db.claim_idempotency_retry(
        idempotency_key="retry-race",
        request_fingerprint="fingerprint",
        expected_status="PARTIAL",
        processing_started_at="2026-10-02T00:00:01+00:00",
    )

    assert first_claim is True
    assert competing_claim is False
    record = db.get_idempotency_record(idempotency_key="retry-race")
    assert record["status"] == "PROCESSING"
    assert record["processing_started_at"] == "2026-10-02T00:00:00+00:00"


def _store_api_report(db, *, report_id="RPT-API-1", vehicle_id="VEH-API-1", observed_at="2026-09-20"):
    return db.create_api_report_with_idempotency(
        idempotency_key=f"key-{report_id}",
        request_fingerprint=f"fingerprint-{report_id}",
        report_id=report_id,
        vehicle_id=vehicle_id,
        vin="VIN-API-1",
        source_id="SRC-API-1",
        source_type="mechanic",
        observed_at=observed_at,
        report_text="Transmission hesitation observed.",
        claim_id=f"CLM-{report_id}",
        issue_candidate="transmission_shift_behavior",
        polarity="supporting",
        submitted_at="2026-09-21T10:00:00+00:00",
        processing_started_at="2026-09-21T10:00:00+00:00",
    )


def test_api_report_persistence_survives_reopening_and_preserves_payload(tmp_path):
    db_file = tmp_path / "durable-api-report.db"
    db = Database(db_file)

    assert _store_api_report(db) is True
    row = db.get_api_report("RPT-API-1")
    assert row is not None
    assert row["vehicle_id"] == "VEH-API-1"
    assert row["vin"] == "VIN-API-1"
    assert row["report_text"] == "Transmission hesitation observed."
    assert row["claim_id"] == "CLM-RPT-API-1"

    reopened = Database(db_file)
    persisted = reopened.get_api_report("RPT-API-1")
    assert persisted is not None
    assert dict(persisted) == dict(row)
    state = reopened.get_idempotency_record(report_id="RPT-API-1")
    assert state is not None
    assert state["status"] == "PROCESSING"


def test_api_report_identity_is_unique_and_keeps_original_record(tmp_path):
    db = Database(tmp_path / "vericar.db")
    assert _store_api_report(db) is True
    assert db.create_api_report_with_idempotency(
        idempotency_key="key-RPT-API-1",
        request_fingerprint="different-fingerprint",
        report_id="RPT-API-2",
        vehicle_id="VEH-API-2",
        vin=None,
        source_id="SRC-API-2",
        source_type="owner",
        observed_at="2026-09-21",
        report_text="Different report.",
        claim_id="CLM-RPT-API-2",
        issue_candidate=None,
        polarity="unresolved",
        submitted_at="2026-09-21T10:00:00+00:00",
        processing_started_at="2026-09-21T10:00:00+00:00",
    ) is False

    original = db.get_api_report("RPT-API-1")
    assert original is not None
    assert original["report_text"] == "Transmission hesitation observed."
    assert db.get_api_report("RPT-API-2") is None


def test_api_reports_are_vehicle_isolated_and_ordered_chronologically(tmp_path):
    db = Database(tmp_path / "vericar.db")
    assert _store_api_report(
        db, report_id="RPT-LATE", vehicle_id="VEH-A", observed_at="2026-09-22"
    )
    assert _store_api_report(
        db, report_id="RPT-EARLY", vehicle_id="VEH-A", observed_at="2026-09-20"
    )
    assert _store_api_report(
        db, report_id="RPT-OTHER", vehicle_id="VEH-B", observed_at="2026-09-19"
    )

    assert [row["report_id"] for row in db.list_api_reports("VEH-A")] == [
        "RPT-EARLY",
        "RPT-LATE",
    ]
    assert [row["report_id"] for row in db.list_api_reports("VEH-B")] == ["RPT-OTHER"]


def test_existing_idempotency_database_migrates_to_durable_api_reports(tmp_path):
    db_file = tmp_path / "legacy.db"
    with closing(sqlite3.connect(db_file)) as connection:
        connection.execute(
            """
            CREATE TABLE report_idempotency (
                idempotency_key TEXT UNIQUE,
                request_fingerprint TEXT NOT NULL,
                report_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                vehicle_memory_status TEXT NOT NULL DEFAULT 'PENDING',
                source_memory_status TEXT NOT NULL DEFAULT 'PENDING',
                resolution_status TEXT NOT NULL DEFAULT 'PENDING',
                response_payload TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            INSERT INTO report_idempotency (
                idempotency_key, request_fingerprint, report_id, status
            ) VALUES ('legacy-key', 'legacy-fingerprint', 'RPT-LEGACY', 'COMPLETED')
            """
        )
        connection.commit()

    migrated = Database(db_file)
    legacy = migrated.get_idempotency_record(report_id="RPT-LEGACY")
    assert legacy is not None
    assert legacy["processing_started_at"] is None
    assert _store_api_report(migrated, report_id="RPT-NEW") is True

    migrated_again = Database(db_file)
    assert migrated_again.get_api_report("RPT-NEW") is not None

