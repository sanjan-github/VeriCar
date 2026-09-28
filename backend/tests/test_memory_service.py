from datetime import datetime, timezone

import pytest

from backend.app.models.memory import VehicleReport
from backend.app.services.memory_service import MemoryService


class FakeRepository:
    def __init__(self):
        self.banks = []
        self.reports = []

    async def ensure_bank(self, **kwargs):
        self.banks.append(kwargs)

    async def retain_report(self, report):
        self.reports.append(("vehicle", report.report_id))
        return {"bank": "vehicle"}

    async def retain_source_report(self, report):
        self.reports.append(("source", report.report_id))
        return {"bank": "source"}

    async def recall_vehicle(self, vin, query):
        return []

    async def recall_source(self, source_id, query):
        return []

    async def reflect(self, vin, assessment_context):
        return ""

    async def check_version(self):
        return {"version": "test"}

    async def close(self):
        return None


@pytest.mark.asyncio
async def test_retain_report_writes_vehicle_and_source_memory():
    repository = FakeRepository()
    service = MemoryService(repository)
    report = VehicleReport(
        report_id="report-1",
        vin="TEST-VIN-001",
        source_id="source-1",
        source_type="inspector",
        text="Transmission hesitation.",
        observed_at=datetime(2026, 9, 20, tzinfo=timezone.utc),
    )

    await service.retain_report(report)

    assert {bank["bank_id"] for bank in repository.banks} == {
        "vehicle_TEST-VIN-001",
        "source_source-1",
    }
    assert repository.reports == [
        ("vehicle", "report-1"),
        ("source", "report-1"),
    ]
