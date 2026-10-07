from datetime import date

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.main import app, get_groq_explanation_service, get_memory_service
from backend.app.models.memory import MemoryEvidence
from core.database import Database, DEFAULT_DB_PATH
from core.models import Car


class AssessmentMemoryService:
    def __init__(self, evidence):
        self.evidence = evidence

    async def recall_vehicle_history(self, vin, query):
        return self.evidence

    async def recall_source_history(self, source_id, query):
        return []

    async def close(self):
        return None


def ensure_test_car(vehicle_id: str = "VEH-001"):
    db = getattr(app.state, "database", None)
    if db is None:
        db = Database(getattr(settings, "db_path", DEFAULT_DB_PATH))
    db.save_car(Car(car_id=vehicle_id, brand="Toyota", model="Corolla", manufacture_year=2020))


def memory(*, memory_id, text, metadata, tags=None):
    return MemoryEvidence(
        memory_id=memory_id,
        text=text,
        metadata=metadata,
        tags=tags or [],
        mentioned_at="2026-09-20T00:00:00+00:00",
    )


def test_get_vehicle_assessment_returns_deterministic_evidence_state():
    app.dependency_overrides.clear()
    ensure_test_car("VEH-001")
    service = AssessmentMemoryService(
        [
            memory(
                memory_id="m-1",
                text="Hard 2-to-3 shift observed.",
                metadata={
                    "report_id": "RPT-1",
                    "source_id": "SRC-M",
                    "source_type": "mechanic",
                    "vehicle_id": "VEH-001",
                    "observed_at": "2026-09-20T00:00:00+00:00",
                    "issue_candidate": "transmission_shift_behavior",
                    "polarity": "supporting",
                },
            ),
            memory(
                memory_id="m-2",
                text="Transmission shifted smoothly.",
                metadata={
                    "report_id": "RPT-2",
                    "source_id": "SRC-O",
                    "source_type": "owner",
                    "vehicle_id": "VEH-001",
                    "observed_at": "2026-09-21T00:00:00+00:00",
                    "issue_candidate": "transmission_shift_behavior",
                    "polarity": "contradicting",
                },
            ),
        ]
    )
    # Route dependency is imported explicitly to avoid requiring a live Hindsight service.
    from backend.app.main import get_memory_service
    app.dependency_overrides[get_memory_service] = lambda: service

    with TestClient(app) as client:
        response = client.get(
            "/api/vehicles/VEH-001/assessment",
            params={"issue": "transmission_shift_behavior"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["vehicle_id"] == "VEH-001"
    assert body["findings"][0]["issue"] == "transmission_shift_behavior"
    assert body["findings"][0]["supporting_sources"] == 1
    assert body["findings"][0]["contradicting_sources"] == 1
    assert body["memory_status"] == "available"
    app.dependency_overrides.clear()


def test_get_vehicle_assessment_distinguishes_memory_unavailable():
    ensure_test_car("VEH-001")
    class UnavailableMemoryService:
        async def recall_vehicle_history(self, vin, query):
            raise RuntimeError("Hindsight unavailable")

    from backend.app.main import get_memory_service
    app.dependency_overrides[get_memory_service] = lambda: UnavailableMemoryService()

    with TestClient(app) as client:
        response = client.get(
            "/api/vehicles/VEH-001/assessment",
            params={"issue": "transmission_shift_behavior"},
        )

    assert response.status_code == 503
    assert response.json()["detail"]["error"]["code"] == "MEMORY_UNAVAILABLE"
    app.dependency_overrides.clear()


def test_groq_failure_keeps_deterministic_assessment_available():
    ensure_test_car("VEH-001")
    class UnavailableExplanationService:
        async def explain(self, assessment):
            raise RuntimeError("Groq unavailable")

    app.dependency_overrides.clear()
    app.dependency_overrides[get_memory_service] = lambda: AssessmentMemoryService(
        [
            memory(
                memory_id="m-groq-failure",
                text="Hesitation during the 2-to-3 shift.",
                metadata={
                    "report_id": "RPT-GROQ-FAILURE",
                    "source_id": "SRC-MECH-GROQ",
                    "source_type": "mechanic",
                    "vehicle_id": "VEH-001",
                    "observed_at": "2026-09-20",
                    "issue_candidate": "transmission_shift_behavior",
                    "polarity": "supporting",
                },
            )
        ]
    )
    app.dependency_overrides[get_groq_explanation_service] = (
        lambda: UnavailableExplanationService()
    )

    with TestClient(app) as client:
        response = client.get(
            "/api/vehicles/VEH-001/assessment/explanation",
            params={"issue": "transmission_shift_behavior"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["memory_status"] == "available"
    assert body["findings"][0]["supporting_sources"] == 1
    assert body["explanation_status"] == "unavailable"
    assert body["explanation"] is None
    app.dependency_overrides.clear()


def test_get_demo_scenarios_returns_scenarios_and_seeds_db():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.get("/api/demo-scenarios")

    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == 3
    keys = [s["key"] for s in data["scenarios"]]
    assert "clean" in keys
    assert "negotiate" in keys
    assert "critical" in keys


def test_create_vehicle_registers_car_and_empty_condition():
    app.dependency_overrides.clear()
    payload = {
        "car_id": "TEST-REG-001",
        "brand": "Hyundai",
        "model": "Creta",
        "manufacture_year": 2021,
        "variant": "SX(O)",
        "fuel_type": "Diesel",
        "transmission": "Automatic",
        "odometer_km": 35000,
        "asking_price_inr": 1200000,
        "previous_owners": 1,
        "vin": "MALTESTVIN001",
        "registration_state": "KA",
    }
    with TestClient(app) as client:
        response = client.post("/api/vehicles", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "created"
    assert data["car_id"] == "TEST-REG-001"
    assert data["vehicle"]["brand"] == "Hyundai"


def test_get_vehicle_assessment_includes_overall_assessment_when_available():
    app.dependency_overrides.clear()
    app.dependency_overrides[get_memory_service] = lambda: AssessmentMemoryService([])
    with TestClient(app) as client:
        # First ensure demo scenarios are seeded
        client.get("/api/demo-scenarios")
        response = client.get("/api/vehicles/DEMO-CLEAN/assessment")

    assert response.status_code == 200
    body = response.json()
    assert body["vehicle_id"] == "DEMO-CLEAN"
    assert "overall_assessment" in body
    assert body["overall_assessment"] is not None
    assert body["overall_assessment"]["verdict"] in ("BUY", "NEGOTIATE", "AVOID")
    assert "confidence" in body["overall_assessment"]
    app.dependency_overrides.clear()
