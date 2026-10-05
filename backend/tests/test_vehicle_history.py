from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import get_database, get_vehicle_history
from core.database import Database
from core.models import Car


def make_app(db: Database) -> FastAPI:
    app = FastAPI()
    app.state.database = db
    app.get("/api/vehicles/{vehicle_id}")(get_vehicle_history)
    app.dependency_overrides[get_database] = lambda: db
    return app


def add_report(
    db: Database,
    *,
    report_id: str,
    vehicle_id: str,
    observed_at: str,
    submitted_at: str,
    text: str,
    source_id: str,
) -> None:
    assert db.create_api_report_with_idempotency(
        idempotency_key=f"key-{report_id}",
        request_fingerprint=f"fingerprint-{report_id}",
        report_id=report_id,
        vehicle_id=vehicle_id,
        vin=None,
        source_id=source_id,
        source_type="mechanic",
        observed_at=observed_at,
        report_text=text,
        claim_id=f"CLM-{report_id}",
        issue_candidate="transmission_shift_behavior",
        polarity="supporting",
        submitted_at=submitted_at,
        processing_started_at=datetime.now(timezone.utc).isoformat(),
    )


def test_vehicle_history_returns_vehicle_and_chronological_reports(tmp_path):
    db = Database(tmp_path / "history.db")
    db.save_car(Car(car_id="CAR-1", brand="Toyota", model="City", manufacture_year=2020))
    add_report(
        db,
        report_id="RPT-2",
        vehicle_id="CAR-1",
        observed_at="2026-10-02T00:00:00+00:00",
        submitted_at="2026-10-02T09:00:00+00:00",
        text="Later observation.",
        source_id="SRC-2",
    )
    add_report(
        db,
        report_id="RPT-1",
        vehicle_id="CAR-1",
        observed_at="2026-09-20T00:00:00+00:00",
        submitted_at="2026-09-20T09:00:00+00:00",
        text="Earlier observation.",
        source_id="SRC-1",
    )

    with TestClient(make_app(db)) as client:
        response = client.get("/api/vehicles/CAR-1")

    assert response.status_code == 200
    body = response.json()
    assert body["vehicle_id"] == "CAR-1"
    assert body["vehicle"]["brand"] == "Toyota"
    assert body["report_count"] == 2
    assert body["history_status"] == "available"
    assert [item["report_id"] for item in body["reports"]] == ["RPT-1", "RPT-2"]
    assert body["reports"][0]["text"] == "Earlier observation."
    assert body["reports"][0]["claim"]["issue_candidate"] == "transmission_shift_behavior"


def test_vehicle_history_is_isolated_by_vehicle_id(tmp_path):
    db = Database(tmp_path / "isolation.db")
    add_report(
        db,
        report_id="RPT-A",
        vehicle_id="CAR-A",
        observed_at="2026-09-20T00:00:00+00:00",
        submitted_at="2026-09-20T09:00:00+00:00",
        text="Vehicle A report.",
        source_id="SRC-A",
    )
    add_report(
        db,
        report_id="RPT-B",
        vehicle_id="CAR-B",
        observed_at="2026-09-21T00:00:00+00:00",
        submitted_at="2026-09-21T09:00:00+00:00",
        text="Vehicle B report.",
        source_id="SRC-B",
    )

    with TestClient(make_app(db)) as client:
        response = client.get("/api/vehicles/CAR-A")

    assert response.status_code == 200
    assert [item["report_id"] for item in response.json()["reports"]] == ["RPT-A"]


def test_vehicle_with_no_reports_returns_empty_history(tmp_path):
    db = Database(tmp_path / "empty.db")
    db.save_car(Car(car_id="CAR-EMPTY", brand="Honda", model="City", manufacture_year=2021))

    with TestClient(make_app(db)) as client:
        response = client.get("/api/vehicles/CAR-EMPTY")

    assert response.status_code == 200
    assert response.json()["reports"] == []
    assert response.json()["report_count"] == 0
    assert response.json()["history_status"] == "empty"


def test_unknown_vehicle_returns_vehicle_not_found(tmp_path):
    db = Database(tmp_path / "missing.db")

    with TestClient(make_app(db)) as client:
        response = client.get("/api/vehicles/DOES-NOT-EXIST")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "VEHICLE_NOT_FOUND"


def test_history_uses_sqlite_even_when_external_memory_is_unavailable(tmp_path):
    db = Database(tmp_path / "local-history.db")
    add_report(
        db,
        report_id="RPT-LOCAL",
        vehicle_id="CAR-LOCAL",
        observed_at="2026-09-20T00:00:00+00:00",
        submitted_at="2026-09-20T09:00:00+00:00",
        text="Durably stored report.",
        source_id="SRC-LOCAL",
    )

    # This endpoint intentionally has no Hindsight dependency: accepted SQLite
    # reports remain authoritative for durable history retrieval.
    with TestClient(make_app(db)) as client:
        response = client.get("/api/vehicles/CAR-LOCAL")

    assert response.status_code == 200
    assert response.json()["reports"][0]["report_id"] == "RPT-LOCAL"
