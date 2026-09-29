from datetime import date

from core.assessment import assess_vehicle
from core.comparison import ComparisonFinding
from core.condition import ConditionRecord, Repair
from core.models import Car
from core.rules import RuleFlag


def car():
    return Car("CAR-1", "Tata", "Nexon", 2022, odometer_km=30000)


def test_critical_rule_produces_avoid():
    condition = ConditionRecord.empty("CAR-1")
    flags = [RuleFlag("vin_rc_match", "critical", "VIN does not match RC.")]
    assessment = assess_vehicle(car(), condition, flags, [])
    assert assessment.verdict == "AVOID"
    assert assessment.confidence >= 75


def test_multiple_warnings_produce_negotiate():
    condition = ConditionRecord.empty("CAR-1")
    flags = [
        RuleFlag("a", "warn", "warning one"),
        RuleFlag("b", "warn", "warning two"),
        RuleFlag("c", "warn", "warning three"),
    ]
    assessment = assess_vehicle(car(), condition, flags, [])
    assert assessment.verdict == "NEGOTIATE"
    assert assessment.negotiation_reduction_inr == 0


def test_clean_evidence_produces_buy_but_unknowns_reduce_confidence():
    condition = ConditionRecord.empty("CAR-1")
    flags = [RuleFlag("unknown_data", "info", "Unknown fields", ("count=2",))]
    assessment = assess_vehicle(car(), condition, flags, [])
    assert assessment.verdict == "BUY"
    assert assessment.confidence == 80


def test_repair_costs_create_range():
    condition = ConditionRecord.empty("CAR-1")
    condition.repairs.append(Repair(date(2025, 1, 1), 25000, "Brakes", "Brake work", 10000, "Independent"))
    assessment = assess_vehicle(car(), condition, [], [])
    assert assessment.near_term_repair_range_inr == (10000, 12500)


def test_unknown_comparison_creates_next_check():
    condition = ConditionRecord.empty("CAR-1")
    findings = [ComparisonFinding("service", "unknown", "No service records were provided.")]
    assessment = assess_vehicle(car(), condition, [], findings)
    assert "Obtain the missing service, repair, document, and inspection evidence." in assessment.next_checks
