from datetime import datetime, timezone
from pathlib import Path
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.main import create_report, get_database, get_memory_service
from backend.app.models.report import (
    REPORT_TEXT_MAX_LENGTH,
    ReportSubmission,
    build_claim,
    generate_report_id,
    to_vehicle_report,
)
from core.database import Database


class FakeMemoryService:
    def __init__(self):
        self.reports = {}
        self.vehicle_calls = 0
        self.source_calls = 0
        self.resolution_calls = 0
        self.fail_vehicle = False
        self.fail_source = False
        self.fail_resolution = False

    async def retain_vehicle_report(self, report):
        if self.fail_vehicle:
            raise RuntimeError("Hindsight vehicle memory unavailable")
        self.vehicle_calls += 1
        return {"bank": f"vehicle_{report.vehicle_id}"}

    async def retain_source_report(self, report):
        if self.fail_source:
            raise RuntimeError("Hindsight source memory unavailable")
        self.source_calls += 1
        return {"bank": f"source_{report.source_id}"}

    async def retain_report(self, report):
        await self.retain_vehicle_report(report)
        await self.retain_source_report(report)
        self.reports[report.report_id] = report
        return {"vehicle": "stored", "source": "stored"}

    async def resolve_source_outcomes(self, report):
        if self.fail_resolution:
            raise RuntimeError("Resolution processing failed")
        self.resolution_calls += 1
        return None


def make_app(memory_service: FakeMemoryService, db: Database | None = None) -> FastAPI:
    if db is None:
        tmp_dir = tempfile.mkdtemp()
        db = Database(Path(tmp_dir) / "test.db")
    app = FastAPI()
    app.state.database = db
    app.state.memory_service = memory_service
    app.post("/api/reports", status_code=201)(create_report)
    app.dependency_overrides[get_memory_service] = lambda: memory_service
    app.dependency_overrides[get_database] = lambda: db
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
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 1
    assert memory.resolution_calls == 1


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
    # Idempotent retry must not repeat persistence calls
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 1
    assert memory.resolution_calls == 1


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
    assert memory.vehicle_calls == 0
    assert memory.source_calls == 0


def test_create_report_returns_503_when_memory_fails():
    memory = FakeMemoryService()
    memory.fail_vehicle = True
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
    assert body["status"] == "failed"
    assert body["report_id"].startswith("RPT-")


# ==============================================================================
# IDEMPOTENCY TESTS (Problems 1 & 2 Requirements)
# ==============================================================================

def test_idempotent_submission_does_not_repeat_persistence_calls(tmp_path):
    """Test 1: Identical request with same Idempotency-Key must not repeat persistence."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-001",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        first = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "abc123"})
        second = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "abc123"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["report"]["report_id"] == second.json()["report"]["report_id"]
    # Assert exact persistence call counts: persistence called once total
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 1
    assert memory.resolution_calls == 1


def test_idempotency_key_with_different_payload_conflicts(tmp_path):
    """Test 2: Same Idempotency-Key with different payload rejected with 4xx conflict."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    app = make_app(memory, db=db)

    payload1 = {
        "vehicle_id": "VEH-001",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }
    payload2 = {
        "vehicle_id": "VEH-001",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Different payload content.",
    }

    with TestClient(app) as client:
        first = client.post("/api/reports", json=payload1, headers={"Idempotency-Key": "conflict-key"})
        second = client.post("/api/reports", json=payload2, headers={"Idempotency-Key": "conflict-key"})

    assert first.status_code == 201
    assert second.status_code == 409
    assert "conflicts" in second.json()["detail"].lower()
    # Ensure no second report persistence occurred
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 1
    assert memory.resolution_calls == 1


@pytest.mark.asyncio
async def test_concurrent_submissions_with_same_idempotency_key(tmp_path):
    """Test 3: Concurrent submissions with same Idempotency-Key result in only one persistence."""
    import asyncio
    import httpx

    db = Database(tmp_path / "test.db")

    class SlowMemoryService(FakeMemoryService):
        async def retain_vehicle_report(self, report):
            await asyncio.sleep(0.05)
            return await super().retain_vehicle_report(report)

    memory = SlowMemoryService()
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-CONCURRENT",
        "source_id": "SRC-CONCURRENT",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed under concurrency.",
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        res1, res2 = await asyncio.gather(
            client.post("/api/reports", json=payload, headers={"Idempotency-Key": "concurrent-key"}),
            client.post("/api/reports", json=payload, headers={"Idempotency-Key": "concurrent-key"}),
        )

    assert res1.status_code == 201
    assert res2.status_code == 201
    assert res1.json()["report"]["report_id"] == res2.json()["report"]["report_id"]
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 1
    assert memory.resolution_calls == 1


def test_idempotency_survives_process_restart(tmp_path):
    """Test 4: Idempotency record persists across app/process restarts via durable SQLite storage."""
    db_file = tmp_path / "durable.db"
    db1 = Database(db_file)
    memory1 = FakeMemoryService()
    app1 = make_app(memory1, db=db1)

    payload = {
        "vehicle_id": "VEH-DURABLE",
        "source_id": "SRC-DURABLE",
        "source_type": "inspector",
        "observed_at": "2026-09-20",
        "text": "Transmission shift smooth.",
    }

    with TestClient(app1) as client1:
        first = client1.post("/api/reports", json=payload, headers={"Idempotency-Key": "restart-key"})

    assert first.status_code == 201
    report_id = first.json()["report"]["report_id"]
    assert memory1.vehicle_calls == 1

    # Simulate fresh process restart with new instances
    memory2 = FakeMemoryService()
    db2 = Database(db_file)
    app2 = make_app(memory2, db=db2)

    with TestClient(app2) as client2:
        retry = client2.post("/api/reports", json=payload, headers={"Idempotency-Key": "restart-key"})

    assert retry.status_code == 201
    assert retry.json()["report"]["report_id"] == report_id
    # Persistence was NOT called on the new memory service
    assert memory2.vehicle_calls == 0
    assert memory2.source_calls == 0
    assert memory2.resolution_calls == 0


# ==============================================================================
# PARTIAL-WRITE TESTS
# ==============================================================================

def test_partial_write_vehicle_succeeds_source_fails(tmp_path):
    """Case 1: Vehicle persistence succeeds, source persistence fails -> PARTIAL."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    memory.fail_source = True
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-PARTIAL-1",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "partial-key-1"})

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "partial"
    assert body["stages"]["vehicle_memory"] == "stored"
    assert body["stages"]["source_memory"] == "failed"
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 0

    record = db.get_idempotency_record(idempotency_key="partial-key-1")
    assert record is not None
    assert record["status"] == "PARTIAL"
    assert record["vehicle_memory_status"] == "STORED"
    assert record["source_memory_status"] == "FAILED"


def test_failed_write_vehicle_fails_before_anything_stored(tmp_path):
    """Case 2: Vehicle persistence fails before anything is stored -> FAILED."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    memory.fail_vehicle = True
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-FAILED-2",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "failed-key-2"})

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "failed"
    assert body["stages"]["vehicle_memory"] == "failed"
    assert memory.vehicle_calls == 0

    record = db.get_idempotency_record(idempotency_key="failed-key-2")
    assert record is not None
    assert record["status"] == "FAILED"
    assert record["vehicle_memory_status"] == "FAILED"


def test_partial_write_reports_succeed_resolution_fails(tmp_path):
    """Case 3: Vehicle + source succeed, resolution fails -> PARTIAL (report persistence recorded)."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    memory.fail_resolution = True
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-PARTIAL-3",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "partial-key-3"})

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "partial"
    assert body["stages"]["vehicle_memory"] == "stored"
    assert body["stages"]["source_memory"] == "stored"
    assert body["stages"]["resolution"] == "failed"
    assert memory.vehicle_calls == 1
    assert memory.source_calls == 1
    assert memory.resolution_calls == 0

    record = db.get_idempotency_record(idempotency_key="partial-key-3")
    assert record is not None
    assert record["status"] == "PARTIAL"
    assert record["vehicle_memory_status"] == "STORED"
    assert record["source_memory_status"] == "STORED"
    assert record["resolution_status"] == "FAILED"


def test_retry_after_partial_failure_completes_safely(tmp_path):
    """Case 4: Retry after partial failure skips already-completed operations and completes safely."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    memory.fail_source = True
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-RETRY-4",
        "source_id": "SRC-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Transmission hesitation observed.",
    }

    with TestClient(app) as client:
        first = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "retry-case-4"})
        assert first.status_code == 503
        assert first.json()["status"] == "partial"
        first_report_id = first.json()["report_id"]
        assert memory.vehicle_calls == 1
        assert memory.source_calls == 0

        # Resolve transient failure
        memory.fail_source = False

        # Retry identical request
        second = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "retry-case-4"})
        assert second.status_code == 201
        assert second.json()["status"] == "complete"
        assert second.json()["report"]["report_id"] == first_report_id

        # Vehicle retention was NOT called again; remaining operations succeeded
        assert memory.vehicle_calls == 1
        assert memory.source_calls == 1
        assert memory.resolution_calls == 1

        record = db.get_idempotency_record(idempotency_key="retry-case-4")
        assert record is not None
        assert record["status"] == "COMPLETED"
        assert record["vehicle_memory_status"] == "STORED"
        assert record["source_memory_status"] == "STORED"
        assert record["resolution_status"] == "STORED"


def test_error_responses_do_not_leak_sensitive_data(tmp_path):
    """Ensure error messages do not leak VINs, payload text, or stack traces."""
    db = Database(tmp_path / "test.db")
    memory = FakeMemoryService()
    memory.fail_source = True
    app = make_app(memory, db=db)

    payload = {
        "vehicle_id": "VEH-SECRET-1",
        "vin": "SECRET-VIN-99999",
        "source_id": "SRC-SECRET-001",
        "source_type": "mechanic",
        "observed_at": "2026-09-20",
        "text": "Extremely secret mechanic findings that should never be in error messages.",
    }

    with TestClient(app) as client:
        response = client.post("/api/reports", json=payload, headers={"Idempotency-Key": "leak-check-key"})

    assert response.status_code == 503
    text = response.text
    assert "SECRET-VIN-99999" not in text
    assert "Extremely secret" not in text
    assert "Traceback" not in text
