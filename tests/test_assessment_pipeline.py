from datetime import date

from core.assessment_pipeline import run_assessment
from core.condition import ConditionRecord
from core.database import Database
from core.models import Car


def test_pipeline_returns_assessment_for_seeded_vehicle(tmp_path):
    db = Database(tmp_path / "test.db")
    car = Car("CAR-1", "Tata", "Nexon", 2022, "XZ+", "Petrol", "Manual", odometer_km=30000)
    condition = ConditionRecord.empty("CAR-1")

    result = run_assessment(car, condition, db, today=date(2026, 1, 1))

    assert result.profile_resolution.status == "FOUND"
    assert result.assessment is not None
    assert result.assessment.verdict in {"BUY", "NEGOTIATE", "AVOID"}
    assert result.rule_flags
    assert result.comparison_findings


def test_pipeline_does_not_invent_profile(tmp_path):
    db = Database(tmp_path / "test.db")
    car = Car("CAR-2", "UnknownBrand", "UnknownModel", 2023)
    condition = ConditionRecord.empty("CAR-2")

    result = run_assessment(car, condition, db, today=date(2026, 1, 1))

    assert result.profile_resolution.status == "MISSING"
    assert result.assessment is None
    assert result.comparison_findings == ()


def test_pipeline_critical_evidence_reaches_assessment(tmp_path):
    db = Database(tmp_path / "test.db")
    car = Car("CAR-3", "Tata", "Nexon", 2022, "XZ+", "Petrol", "Manual", odometer_km=30000)
    condition = ConditionRecord.empty("CAR-3")
    condition.documents["vin_matches_rc"] = "No"

    result = run_assessment(car, condition, db, today=date(2026, 1, 1))

    assert result.assessment is not None
    assert result.assessment.verdict == "AVOID"
    assert result.assessment.critical_findings


def test_pipeline_reconciles_supplied_history_without_changing_assessment(tmp_path):
    from datetime import datetime
    from core.memory_report import build_vehicle_memory_report
    from memory.hindsight import MemoryItem

    db = Database(tmp_path / "test.db")
    car = Car(
        "CAR-HISTORY", "Tata", "Nexon", 2022,
        "XZ+", "Petrol", "Manual", odometer_km=30000
    )
    condition = ConditionRecord.empty(car.car_id)
    report = build_vehicle_memory_report(
        car,
        condition,
        observed_at=datetime(2026, 1, 1),
    )
    history_item = MemoryItem(
        memory_id="memory-1",
        text=report.text,
        metadata={**report.metadata, "observed_at": report.observed_at.isoformat()},
        tags=[f"vehicle:{car.car_id}"],
    )

    result = run_assessment(
        car, condition, db, today=date(2026, 1, 1),
        history_items=[history_item],
    )

    assert result.assessment is not None
    assert result.history_reconciliation is not None
    assert result.history_reconciliation.status == "MATCHED"
    assert result.assessment.verdict in {"BUY", "NEGOTIATE", "AVOID"}


def test_pipeline_keeps_history_optional(tmp_path):
    db = Database(tmp_path / "test.db")
    car = Car("CAR-NO-HISTORY", "Tata", "Nexon", 2022)
    condition = ConditionRecord.empty(car.car_id)

    result = run_assessment(car, condition, db, today=date(2026, 1, 1))

    assert result.history_reconciliation is None
