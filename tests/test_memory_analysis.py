from datetime import datetime, timezone

from core.condition import ConditionRecord, Repair
from core.history_reconciliation import reconcile_vehicle_history
from core.memory_analysis import analyze_longitudinal_memory
from core.memory_report import build_vehicle_memory_report
from core.models import Car
from memory.hindsight import MemoryItem


def make_car(odometer_km: int, car_id: str = "CAR-LONG") -> Car:
    return Car(
        car_id=car_id,
        brand="Toyota",
        model="City",
        manufacture_year=2020,
        vin="VIN-LONG-1",
        odometer_km=odometer_km,
    )


def make_item(car: Car, condition: ConditionRecord, report_id: str, observed_at: datetime) -> MemoryItem:
    report = build_vehicle_memory_report(car, condition, observed_at=observed_at)
    metadata = {
        **report.metadata,
        "report_id": report_id,
        "observed_at": report.observed_at.isoformat(),
    }
    return MemoryItem(
        memory_id=f"memory-{report_id}",
        text=report.text,
        metadata=metadata,
        tags=[f"vehicle:{car.car_id}"],
    )


def test_longitudinal_history_preserves_multiple_snapshots_and_detects_regression():
    c1 = make_car(80_000)
    c2 = make_car(84_000)
    c3 = make_car(76_000)
    condition = ConditionRecord.empty(c1.car_id)

    items = [
        make_item(c1, condition, "R1", datetime(2026, 7, 1, tzinfo=timezone.utc)),
        make_item(c2, condition, "R2", datetime(2026, 8, 1, tzinfo=timezone.utc)),
        make_item(c3, condition, "R3", datetime(2026, 9, 1, tzinfo=timezone.utc)),
    ]

    result = reconcile_vehicle_history(c3, condition, items)

    assert len(result.snapshots) == 3
    assert result.snapshots[0].report_id == "R3"
    assert any(
        f.field == "odometer_km" and f.kind == "CONTRADICTION"
        for f in result.longitudinal_findings
    )


def test_unknown_does_not_create_longitudinal_contradiction():
    c1 = make_car(80_000)
    c2 = make_car(82_000)
    first = ConditionRecord.empty(c1.car_id)
    second = ConditionRecord.empty(c2.car_id)
    first.accident_status = "Yes"
    second.accident_status = "Unknown"

    items = [
        make_item(c1, first, "R1", datetime(2026, 7, 1, tzinfo=timezone.utc)),
        make_item(c2, second, "R2", datetime(2026, 8, 1, tzinfo=timezone.utc)),
    ]

    result = reconcile_vehicle_history(c2, second, items)

    assert not any(
        f.field == "accident_status" for f in result.longitudinal_findings
    )


def test_influential_memory_is_derived_from_contradiction():
    historical = make_car(90_000)
    current = make_car(80_000)
    historical_condition = ConditionRecord.empty(historical.car_id)
    current_condition = ConditionRecord.empty(current.car_id)

    item = make_item(
        historical,
        historical_condition,
        "R-HIST",
        datetime(2026, 8, 1, tzinfo=timezone.utc),
    )
    result = reconcile_vehicle_history(current, current_condition, [item])
    analysis = analyze_longitudinal_memory(current, current_condition, result)

    assert any(
        item.report_id == "R-HIST" and item.field == "odometer_km"
        for item in analysis.influential_memories
    )


def test_model_observation_requires_multiple_distinct_vehicles():
    car1 = make_car(50_000)
    car2 = make_car(55_000)
    condition1 = ConditionRecord.empty(car1.car_id)
    condition2 = ConditionRecord.empty(car2.car_id)
    repair = Repair(
        observed_at=datetime(2026, 7, 1, tzinfo=timezone.utc).date(),
        odometer_km=49_000,
        category="Brakes",
        description="Brake service",
        cost_inr=5000,
        garage_type="Authorized",
    )
    condition1.repairs.append(repair)
    condition2.repairs.append(repair)

    items = [
        make_item(car1, condition1, "R1", datetime(2026, 7, 1, tzinfo=timezone.utc)),
        make_item(car2, condition2, "R2", datetime(2026, 8, 1, tzinfo=timezone.utc)),
    ]
    reconciliation = reconcile_vehicle_history(car2, condition2, items)
    analysis = analyze_longitudinal_memory(car2, condition2, reconciliation)

    assert analysis.model_observations == ()
