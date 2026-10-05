from datetime import datetime, timezone
import sqlite3

from core.database import Database


def test_memory_report_status_persists(tmp_path):
    db = Database(tmp_path / "vericar.db")
    observed_at = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc).isoformat()
    db.record_memory_report(report_id="RPT-1", car_id="CAR-1", observed_at=observed_at, status="synced", synced_at=observed_at)
    row = db.get_memory_report("RPT-1")
    assert row["car_id"] == "CAR-1"
    assert row["status"] == "synced"
    assert row["synced_at"] == observed_at


def test_database_connection_is_closed_after_context(tmp_path):
    db = Database(tmp_path / "vericar.db")

    with db._connect() as connection:
        connection.execute("SELECT 1")

    try:
        connection.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        pass
    else:
        raise AssertionError("Database connection remained open after context exit")


def test_memory_report_status_does_not_require_car_row(tmp_path):
    db = Database(tmp_path / "vericar.db")
    db.record_memory_report(
        report_id="RPT-1",
        car_id="CAR-1",
        observed_at="2026-09-28T10:00:00+00:00",
        status="pending",
    )

    row = db.get_memory_report("RPT-1")
    assert row["car_id"] == "CAR-1"
    assert row["status"] == "pending"


def test_legacy_memory_report_foreign_key_is_migrated(tmp_path):
    db_path = tmp_path / "legacy.db"
    import sqlite3

    connection = sqlite3.connect(db_path)
    connection.execute(
        """
        CREATE TABLE cars (
            car_id TEXT PRIMARY KEY,
            brand TEXT NOT NULL,
            model TEXT NOT NULL,
            manufacture_year INTEGER NOT NULL
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE vehicle_memory_reports (
            report_id TEXT PRIMARY KEY,
            car_id TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            status TEXT NOT NULL,
            error TEXT,
            synced_at TEXT,
            FOREIGN KEY(car_id) REFERENCES cars(car_id)
        )
        """
    )
    connection.execute(
        "INSERT INTO vehicle_memory_reports VALUES (?, ?, ?, ?, ?, ?)",
        ("RPT-LEGACY", "CAR-MISSING", "2026-09-28T10:00:00+00:00", "pending", None, None),
    )
    connection.commit()
    connection.close()

    db = Database(db_path)
    db.record_memory_report(
        report_id="RPT-NEW",
        car_id="CAR-NEW",
        observed_at="2026-09-28T11:00:00+00:00",
        status="pending",
    )

    with db._connect() as connection:
        assert connection.execute("PRAGMA foreign_key_list(vehicle_memory_reports)").fetchall() == []

    assert db.get_memory_report("RPT-LEGACY")["car_id"] == "CAR-MISSING"
    assert db.get_memory_report("RPT-NEW")["car_id"] == "CAR-NEW"
