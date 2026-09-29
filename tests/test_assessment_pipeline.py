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
