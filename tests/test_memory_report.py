from datetime import datetime, timezone

from core.condition import ConditionRecord, Repair
from core.memory_report import build_vehicle_memory_report
from core.models import Car


def test_memory_report_is_evidence_only_and_contains_vehicle_memory_key():
    car = Car(car_id="CAR-1", brand="Toyota", model="Corolla", manufacture_year=2018, vin="VIN-123", odometer_km=82000)
    condition = ConditionRecord.empty("CAR-1")
    report = build_vehicle_memory_report(car, condition, observed_at=datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc))
    assert report.report_id.startswith("RPT-")
    assert report.vehicle_id == "CAR-1"
    assert report.metadata["memory_key"] == "VIN-123"
    assert report.metadata["source_type"] == "user_entered_evidence"
    assert "diagnosis or verdict" in report.text
    assert "Unknown" in report.text


def test_memory_report_preserves_repair_evidence():
    car = Car(car_id="CAR-2", brand="Honda", model="City", manufacture_year=2020)
    condition = ConditionRecord.empty("CAR-2")
    condition.repairs.append(Repair(datetime(2026, 9, 20).date(), 80000, "Transmission", "Clutch replacement reported", 45000, "Independent"))
    report = build_vehicle_memory_report(car, condition)
    assert '"Transmission"' in report.text
    assert '"Clutch replacement reported"' in report.text



def test_identical_evidence_produces_stable_report_id():
    car = Car(car_id="CAR-IDEMPOTENT", brand="Toyota", model="City", manufacture_year=2020)
    condition = ConditionRecord.empty(car.car_id)
    first = build_vehicle_memory_report(
        car, condition, observed_at=datetime(2026, 9, 30, 10, 0, tzinfo=timezone.utc)
    )
    second = build_vehicle_memory_report(
        car, condition, observed_at=datetime(2026, 10, 1, 10, 0, tzinfo=timezone.utc)
    )

    assert first.report_id == second.report_id
