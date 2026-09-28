from datetime import datetime, timezone

import pytest

from backend.app.models.memory import VehicleReport
from backend.app.repositories.hindsight_repository import HindsightRepository


class FakeHindsight:
    def __init__(self):
        self.calls = []

    async def acreate_bank(self, **kwargs):
        self.calls.append(("create_bank", kwargs))

    async def aretain(self, **kwargs):
        self.calls.append(("retain", kwargs))
        return {"ok": True}

    async def arecall(self, **kwargs):
        self.calls.append(("recall", kwargs))
        return {"results": [{"id": "memory-1", "text": "Hard 2-to-3 transmission shift.", "type": "observation", "metadata": {"source_id": "source-1"}, "tags": ["vehicle:VEH-001"], "document_id": "report-report-1"}]}

    async def areflect(self, **kwargs):
        self.calls.append(("reflect", kwargs))
        return {"text": "The later inspection added supporting evidence."}

    async def aget_version(self):
        return {"version": "test"}

    async def aclose(self):
        self.calls.append(("close", {}))


@pytest.mark.asyncio
async def test_retain_report_uses_stable_vehicle_identifier():
    fake = FakeHindsight()
    repository = HindsightRepository(fake)
    report = VehicleReport(
        report_id="report-1", vehicle_id="VEH-001", vin="TEST-VIN-001",
        source_id="source-1", source_type="inspector",
        text="Hard 2-to-3 transmission shift.",
        observed_at=datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc),
    )

    await repository.retain_report(report)

    name, kwargs = fake.calls[-1]
    assert name == "retain"
    assert kwargs["bank_id"] == "vehicle_VEH-001"
    assert kwargs["document_id"] == "report_report-1"
    assert kwargs["metadata"]["vehicle_id"] == "VEH-001"
    assert kwargs["metadata"]["vin"] == "TEST-VIN-001"
    assert kwargs["timestamp"] == report.observed_at
    assert kwargs["retain_async"] is False


@pytest.mark.asyncio
async def test_retain_source_outcome_preserves_resolution_metadata():
    fake = FakeHindsight()
    repository = HindsightRepository(fake)
    resolved_at = datetime(2026, 9, 20, tzinfo=timezone.utc)
    recorded_at = datetime(2026, 9, 22, tzinfo=timezone.utc)

    await repository.retain_source_outcome(
        source_id="SRC-1",
        source_type="mechanic",
        vehicle_id="VEH-1",
        report_id="RPT-OLD",
        triggering_report_id="RPT-NEW",
        issue_candidate="transmission_shift_behavior",
        resolution_status="corroborated",
        resolved_at=resolved_at,
        recorded_at=recorded_at,
    )

    _, kwargs = fake.calls[-1]
    assert kwargs["bank_id"] == "source_SRC-1"
    assert kwargs["document_id"] == "resolution_RPT-OLD_RPT-NEW"
    assert kwargs["metadata"]["resolved_report_id"] == "RPT-OLD"
    assert kwargs["metadata"]["triggering_report_id"] == "RPT-NEW"
    assert kwargs["metadata"]["resolution_status"] == "corroborated"
    assert kwargs["timestamp"] == resolved_at


@pytest.mark.asyncio
async def test_recall_normalizes_evidence_without_scoring_it():
    fake = FakeHindsight()
    repository = HindsightRepository(fake)

    evidence = await repository.recall_vehicle("VEH-001", "transmission problems")

    assert len(evidence) == 1
    assert evidence[0].memory_id == "memory-1"
    assert evidence[0].text == "Hard 2-to-3 transmission shift."
    assert evidence[0].metadata["source_id"] == "source-1"
    assert fake.calls[-1][1]["bank_id"] == "vehicle_VEH-001"


@pytest.mark.asyncio
async def test_reflect_returns_only_hindsight_explanation_text():
    fake = FakeHindsight()
    repository = HindsightRepository(fake)

    explanation = await repository.reflect("VEH-001", "assessment changed")

    assert explanation == "The later inspection added supporting evidence."
