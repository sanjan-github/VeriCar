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
