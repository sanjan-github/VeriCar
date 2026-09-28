from datetime import datetime, timezone

import pytest

from backend.app.models.memory import MemoryEvidence, VehicleReport
from backend.app.services.memory_service import MemoryService


class FakeRepository:
    def __init__(self):
        self.banks = []
        self.reports = []
        self.source_outcomes = []
        self.vehicle_history = []

    async def ensure_bank(self, **kwargs):
        self.banks.append(kwargs)

    async def retain_report(self, report):
        self.reports.append(("vehicle", report.report_id))
        return {"bank": "vehicle"}

    async def retain_source_report(self, report):
        self.reports.append(("source", report.report_id))
        return {"bank": "source"}

    async def retain_source_outcome(self, **kwargs):
        self.source_outcomes.append(kwargs)

    async def recall_vehicle(self, vehicle_id, query):
        return self.vehicle_history

    async def recall_source(self, source_id, query):
        return []

    async def reflect(self, vehicle_id, assessment_context):
        return ""

    async def check_version(self):
        return {"version": "test"}

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_retain_report_uses_vehicle_id_for_vehicle_memory():
    repository = FakeRepository()
    service = MemoryService(repository)
    report = VehicleReport(
        report_id="report-1",
        vehicle_id="VEH-001",
        vin="TEST-VIN-001",
        source_id="source-1",
        source_type="inspector",
        text="Transmission hesitation.",
        observed_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    await service.retain_report(report)

    assert {bank["bank_id"] for bank in repository.banks} == {
        "vehicle_VEH-001",
        "source_source-1",
    }
    assert repository.reports == [
        ("vehicle", "report-1"),
        ("source", "report-1"),
    ]


@pytest.mark.asyncio
async def test_new_independent_report_records_source_outcomes():
    repository = FakeRepository()
    repository.vehicle_history = [
        MemoryEvidence(
            memory_id="memory-old",
            text="Transmission hesitation.",
            metadata={
                "report_id": "RPT-OLD",
                "vehicle_id": "VEH-001",
                "source_id": "SRC-OLD",
                "source_type": "mechanic",
                "issue_candidate": "transmission_shift_behavior",
                "polarity": "supporting",
            },
        )
    ]
    service = MemoryService(repository)
    report = VehicleReport(
        report_id="RPT-NEW",
        vehicle_id="VEH-001",
        vin="VIN-001",
        source_id="SRC-NEW",
        source_type="inspector",
        text="Hard shifting observed.",
        observed_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
        submitted_at=datetime(2026, 9, 22, tzinfo=timezone.utc),
        issue_candidate="transmission_shift_behavior",
        polarity="supporting",
    )

    await service.resolve_source_outcomes(report)

    assert {event["report_id"] for event in repository.source_outcomes} == {
        "RPT-OLD",
        "RPT-NEW",
    }
    assert {event["resolution_status"] for event in repository.source_outcomes} == {
        "corroborated"
    }
    assert all(event["triggering_report_id"] == "RPT-NEW" for event in repository.source_outcomes)
