from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import create_report, get_memory_service
from backend.app.models.report import (
    REPORT_TEXT_MAX_LENGTH,
    ReportSubmission,
    build_claim,
    generate_report_id,
    to_vehicle_report,
)


class FakeMemoryService:
    def __init__(self):
        self.reports = []

    async def retain_report(self, report):
        self.reports.append(report)
        return {"vehicle": "stored", "source": "stored"}

    async def resolve_source_outcomes(self, report):
        return None


def make_app(memory_service: FakeMemoryService) -> FastAPI:
    app = FastAPI()
    app.post("/api/reports", status_code=201)(create_report)
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    return app


def test_report_submission_rejects_invalid_source_type():
    with pytest.raises(ValueError):
        ReportSubmission(
            vehicle_id="VEH-001",
            source_id="SRC-001",
            source_type="random_user",
            observed_at="2026-09-20",
            text="Transmission hesitation.",
        )


def test_report_submission_rejects_blank_text():
    with pytest.raises(ValueError):
        ReportSubmission(
            vehicle_id="VEH-001",
            source_id="SRC-001",
            source_type="owner",
            observed_at="2026-09-20",
            text="   ",
        )


def test_report_submission_rejects_oversized_text():
    with pytest.raises(ValueError):
        ReportSubmission(
            vehicle_id="VEH-001",
            source_id="SRC-001",
            source_type="owner",
            observed_at="2026-09-20",
            text="x" * (REPORT_TEXT_MAX_LENGTH + 1),
        )


def test_to_vehicle_report_normalizes_date_to_utc_midnight():
    request = ReportSubmission(
        vehicle_id="VEH-001",
        vin="VIN-001",
        source_id="SRC-001",
        source_type="mechanic",
        observed_at="2026-09-20",
        text="Transmission hesitation.",
    )
    submitted_at = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)

    report = to_vehicle_report("RPT-001", request, submitted_at)

    assert report.observed_at == datetime(2026, 9, 20, tzinfo=timezone.utc)
    assert report.vehicle_id == "VEH-001"
    assert report.submitted_at == submitted_at


def test_to_vehicle_report_keeps_vin_optional_and_separate_from_vehicle_id():
    request = ReportSubmission(
        vehicle_id="VEH-001",
        source_id="SRC-001",
        source_type="inspector",
        observed_at="2026-09-20",
        text="Transmission hesitation.",
    )

    report = to_vehicle_report(
        "RPT-001",
        request,
        datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
    )

    assert report.vehicle_id == "VEH-001"
    assert report.vin is None


def test_build_claim_normalizes_transmission_issue():
    claim = build_claim(
        "RPT-001",
        "Transmission hesitation confirmed during test drive.",
    )

    assert claim.report_id == "RPT-001"
    assert claim.issue_candidate == "transmission_shift_behavior"
    assert claim.polarity == "supporting"
    assert "Transmission hesitation" in claim.text


def test_build_claim_recognizes_negative_observation():
    claim = build_claim("RPT-001", "Transmission works perfectly.")

    assert claim.issue_candidate == "transmission_shift_behavior"
    assert claim.polarity == "contradicting"


def test_build_claim_leaves_unrelated_text_unresolved():
    claim = build_claim("RPT-001", "Vehicle was parked outside.")

    assert claim.issue_candidate is None
    assert claim.polarity == "unresolved"


def test_report_id_is_stable_for_idempotency_key_and_request():
    first = generate_report_id("request-123", '{"vehicle_id":"VEH-001"}')
    retry = generate_report_id("request-123", '{"vehicle_id":"VEH-001"}')
    changed_request = generate_report_id("request-123", '{"vehicle_id":"VEH-002"}')

    assert first == retry
    assert first != changed_request
    assert first.startswith("RPT-")


def test_create_report_endpoint():
    memory = FakeMemoryService()
    app = make_app(memory)

    payload = {
        "vehicle_id": "VEH-001",
        "vin": "VIN-001",
        "source_id": "SRC-001",
        "source_type": "inspector",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload)

    assert response.status_code == 201
    body = response.json()

    assert body["report"]["status"] == "active"
    assert body["report"]["vehicle_id"] == "VEH-001"
    assert body["report"]["observed_at"] == "2026-09-20"
    assert body["claim"]["report_id"] == body["report"]["report_id"]
    assert body["memory"] == {
        "vehicle_memory": "stored",
        "source_memory": "stored",
    }
    assert len(memory.reports) == 1


def test_create_report_retry_reuses_report_identity():
    memory = FakeMemoryService()
    app = make_app(memory)
    payload = {
        "vehicle_id": "VEH-001",
        "source_id": "SRC-001",
        "source_type": "inspector",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        first = client.post(
            "/api/reports",
            json=payload,
            headers={"Idempotency-Key": "request-123"},
        )
        retry = client.post(
            "/api/reports",
            json=payload,
            headers={"Idempotency-Key": "request-123"},
        )

    assert first.status_code == 201
    assert retry.status_code == 201
    assert first.json()["report"]["report_id"] == retry.json()["report"]["report_id"]
    assert [report.report_id for report in memory.reports] == [
        first.json()["report"]["report_id"],
        first.json()["report"]["report_id"],
    ]


def test_create_report_rejects_invalid_input_before_memory_write():
    memory = FakeMemoryService()
    app = make_app(memory)

    payload = {
        "vehicle_id": "VEH-001",
        "source_id": "SRC-001",
        "source_type": "invalid",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload)

    assert response.status_code == 422
    assert memory.reports == []


def test_create_report_returns_503_when_memory_fails():
    class FailingMemoryService(FakeMemoryService):
        async def retain_report(self, report):
            raise RuntimeError("Hindsight unavailable")

    memory = FailingMemoryService()
    app = make_app(memory)

    payload = {
        "vehicle_id": "VEH-001",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload)

    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["error"] == "partial_failure"
    assert body["detail"]["report_id"].startswith("RPT-")
