from datetime import date

from core.condition import ConditionRecord, Repair, Service
from core.models import Car
from core.rules import (
    check_flood_indicators,
    check_odometer_vs_age,
    check_recurring_repairs,
    check_service_gaps,
    check_service_odometer_order,
    check_vin_rc_match,
    count_unknowns,
    evaluate_rules,
)


def test_odometer_below_expected_range_is_flagged():
    car = Car(
        car_id="CAR-1",
        brand="Tata",
        model="Sierra",
        manufacture_year=2020,
        manufacture_month=1,
        odometer_km=10_000,
    )
    flags = check_odometer_vs_age(
        car,
        today=date(2026, 1, 1),
        annual_km_low=8_000,
        annual_km_high=15_000,
    )
    assert flags
    assert flags[0].severity == "warn"


def test_odometer_within_range_is_not_flagged():
    car = Car(
        car_id="CAR-1",
        brand="Tata",
        model="Sierra",
        manufacture_year=2020,
        manufacture_month=1,
        odometer_km=55_000,
    )
    assert check_odometer_vs_age(
        car,
        today=date(2026, 1, 1),
        annual_km_low=8_000,
        annual_km_high=15_000,
    ) == []


def test_service_reading_above_current_odometer_is_critical():
    car = Car(
        car_id="CAR-1",
        brand="Tata",
        model="Sierra",
        manufacture_year=2020,
        odometer_km=40_000,
    )
    services = [
        Service(date(2025, 1, 1), 45_000, "Routine service"),
    ]
    flags = check_service_odometer_order(car, services)
    assert flags[0].severity == "critical"


def test_service_gap_is_flagged():
    services = [
        Service(date(2024, 1, 1), 20_000, "Service"),
        Service(date(2025, 8, 1), 35_000, "Service"),
    ]
    flags = check_service_gaps(
        services,
        today=date(2025, 9, 1),
        expected_interval_months=12,
        grace_months=3,
    )
    assert len(flags) == 1
    assert flags[0].severity == "warn"


def test_recurring_repair_category_is_flagged():
    repairs = [
        Repair(date(2024, 3, 1), 30_000, "Transmission", "Clutch", 20_000, "Independent"),
        Repair(date(2025, 5, 1), 45_000, "Transmission", "Clutch again", 18_000, "Independent"),
    ]
    flags = check_recurring_repairs(repairs)
    assert len(flags) == 1
    assert flags[0].rule == "recurring_repair"


def test_flood_requires_two_positive_indicators_for_critical():
    condition = ConditionRecord.empty("CAR-1")
    condition.physical_inspection["flood_signs"] = "Yes"
    condition.physical_inspection["rust"] = "Yes"
    flags = check_flood_indicators(condition)
    assert flags[0].severity == "critical"


def test_vin_rc_mismatch_is_critical():
    condition = ConditionRecord.empty("CAR-1")
    condition.documents["vin_matches_rc"] = "No"
    flags = check_vin_rc_match(condition)
    assert flags[0].severity == "critical"


def test_unknown_values_are_counted_without_becoming_flags_for_each_field():
    condition = ConditionRecord.empty("CAR-1")
    assert count_unknowns(condition) == 22


def test_evaluate_rules_keeps_unknown_information_explicit():
    car = Car("CAR-1", "Tata", "Sierra", 2024, odometer_km=4_000)
    condition = ConditionRecord.empty("CAR-1")
    flags = evaluate_rules(car, condition, today=date(2026, 1, 1))
    assert any(flag.rule == "unknown_data" for flag in flags)
    assert any(flag.rule == "vin_rc_match" for flag in flags)
