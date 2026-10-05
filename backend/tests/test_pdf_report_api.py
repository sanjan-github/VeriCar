from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import get_database, get_pdf_report_service, download_vehicle_assessment_pdf
from backend.app.services.pdf_report_service import PdfReportService
from core.database import Database
from core.demo_scenarios import get_demo_scenario


def make_app(db: Database) -> FastAPI:
    app = FastAPI()
    app.get("/api/vehicles/{vehicle_id}/assessment/report.pdf")(
        download_vehicle_assessment_pdf
    )
    app.dependency_overrides[get_database] = lambda: db
    app.dependency_overrides[get_pdf_report_service] = lambda: PdfReportService(db)
    return app


def test_pdf_endpoint_returns_assessment_pdf_for_saved_vehicle(tmp_path):
    scenario = get_demo_scenario("critical")
    db = Database(tmp_path / "report-api.db")
    db.save_car(scenario.car)
    db.save_condition(scenario.condition)

    with TestClient(make_app(db)) as client:
        response = client.get(
            f"/api/vehicles/{scenario.car.car_id}/assessment/report.pdf"
        )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"] == (
        f'attachment; filename="vericar-assessment-{scenario.car.car_id}.pdf"'
    )
    assert response.content.startswith(b"%PDF")


def test_pdf_endpoint_requires_saved_condition(tmp_path):
    scenario = get_demo_scenario("clean")
    db = Database(tmp_path / "missing-condition.db")
    db.save_car(scenario.car)

    with TestClient(make_app(db)) as client:
        response = client.get(
            f"/api/vehicles/{scenario.car.car_id}/assessment/report.pdf"
        )

    assert response.status_code == 409
    assert response.json()["detail"]["error"]["code"] == "CONDITION_NOT_AVAILABLE"


def test_pdf_endpoint_distinguishes_unknown_vehicle(tmp_path):
    db = Database(tmp_path / "missing-vehicle.db")

    with TestClient(make_app(db)) as client:
        response = client.get("/api/vehicles/DOES-NOT-EXIST/assessment/report.pdf")

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "VEHICLE_NOT_FOUND"


def test_pdf_service_does_not_depend_on_hindsight(tmp_path):
    scenario = get_demo_scenario("clean")
    db = Database(tmp_path / "local-only.db")
    db.save_car(scenario.car)
    db.save_condition(scenario.condition)

    pdf = PdfReportService(db).build_vehicle_report(
        vehicle_id=scenario.car.car_id,
        today=date(2026, 9, 29),
    )

    assert pdf.startswith(b"%PDF")
