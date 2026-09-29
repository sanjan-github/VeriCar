from datetime import date

from core.comparison import compare_expected_vs_actual
from core.condition import ConditionRecord, Repair, Service
from core.expected_profile import ExpectedProfile
from core.models import Car


def profile():
    return ExpectedProfile("Tata", "Nexon", 2022, "XZ+", "Petrol", "Manual", 8000, 15000, 12, ["Clutch wear can appear with heavy city use"], ["Annual service"], "synthetic_seed")


def car(km=30000):
    return Car("CAR-1", "Tata", "Nexon", 2022, "XZ+", "Petrol", "Manual", odometer_km=km)


def test_high_mileage_creates_comparison_finding():
    findings = compare_expected_vs_actual(car(70000), ConditionRecord.empty("CAR-1"), profile(), today=date(2026, 1, 1))
    assert any(f.category == "mileage" and f.severity == "warn" for f in findings)


def test_missing_odometer_is_unknown_not_invented():
    findings = compare_expected_vs_actual(car(None), ConditionRecord.empty("CAR-1"), profile(), today=date(2026, 1, 1))
    assert any(f.category == "mileage" and f.severity == "unknown" for f in findings)


def test_service_evidence_is_reported_without_verdict():
    condition = ConditionRecord.empty("CAR-1")
    condition.services.append(Service(date(2025, 1, 1), 20000, "Routine service"))
    findings = compare_expected_vs_actual(car(), condition, profile(), today=date(2026, 1, 1))
    assert any(f.category == "service" for f in findings)
    assert all(f.message not in {"BUY", "NEGOTIATE", "AVOID"} for f in findings)


def test_known_issue_related_repair_is_preserved_as_evidence():
    condition = ConditionRecord.empty("CAR-1")
    condition.repairs.append(Repair(date(2025, 5, 1), 25000, "Transmission", "Clutch replacement", 25000, "Authorized"))
    findings = compare_expected_vs_actual(car(), condition, profile(), today=date(2026, 1, 1))
    assert any(f.category == "known_issue" for f in findings)


def test_empty_history_remains_explicitly_unknown():
    findings = compare_expected_vs_actual(car(), ConditionRecord.empty("CAR-1"), profile(), today=date(2026, 1, 1))
    assert any(f.category == "service" and f.severity == "unknown" for f in findings)
    assert any(f.category == "repairs" and f.severity == "unknown" for f in findings)
