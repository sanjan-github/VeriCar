from datetime import date

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.models.memory import MemoryEvidence
from backend.app.services.evidence_service import EvidenceService


class AssessmentMemoryService:
    def __init__(self, evidence):
        self.evidence = evidence

    async def recall_vehicle_history(self, vin, query):
        return self.evidence

    async def close(self):
        return None


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
