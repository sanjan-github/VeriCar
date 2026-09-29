from datetime import datetime, timezone

from core.condition import ConditionRecord, Repair
from core.history_reconciliation import reconcile_vehicle_history
from core.memory_report import build_vehicle_memory_report
from core.models import Car
from memory.hindsight import MemoryItem


def make_car(odometer_km=50_000):
    return Car(
        car_id="CAR-HISTORY",
        brand="Toyota",
        model="City",
        manufacture_year=2020,
        vin="VIN-HISTORY-1",
        odometer_km=odometer_km,
    )


def make_item(car, condition, report_id="RPT-HISTORY-1", observed_at=None):
    report = build_vehicle_memory_report(
        car,
        condition,
        observed_at=observed_at
        or datetime(2026, 9, 1, tzinfo=timezone.utc),
    )
    return MemoryItem(
        memory_id="memory-1",
        text=report.text,
        metadata={
            **report.metadata,
            "report_id": report_id,
            "observed_at": report.observed_at.isoformat(),
        },
        tags=[f"vehicle:{car.car_id}"],
    )


def test_history_reconciliation_detects_match():
    car = make_car()
    condition = ConditionRecord.empty(car.car_id)

    result = reconcile_vehicle_history(
        car,
        condition,
        [make_item(car, condition)],
    )

    assert result.status == "MATCHED"
    assert any(item.kind == "MATCH" for item in result.findings)
    assert result.snapshots[0].report_id == "RPT-HISTORY-1"


def test_history_reconciliation_detects_odometer_regression():
    historical_car = make_car(odometer_km=60_000)
    current_car = make_car(odometer_km=55_000)
    condition = ConditionRecord.empty(current_car.car_id)
    historical_condition = ConditionRecord.empty(historical_car.car_id)

    result = reconcile_vehicle_history(
        current_car,
        condition,
        [make_item(historical_car, historical_condition)],
    )

    assert result.status == "CONTRADICTION"
    finding = next(item for item in result.findings if item.field == "odometer_km")
    assert finding.kind == "CONTRADICTION"


def test_history_reconciliation_detects_historical_fact_conflict():
    historical_car = make_car()
    current_car = make_car()
    historical_condition = ConditionRecord.empty(historical_car.car_id)
    historical_condition.accident_status = "Yes"

    current_condition = ConditionRecord.empty(current_car.car_id)
    current_condition.accident_status = "No"

    result = reconcile_vehicle_history(
        current_car,
        current_condition,
        [make_item(historical_car, historical_condition)],
    )

    assert result.status == "CONTRADICTION"
    finding = next(
        item for item in result.findings if item.field == "accident_status"
    )
    assert finding.kind == "CONTRADICTION"


def test_history_reconciliation_detects_new_repair_as_change():
    historical_car = make_car()
    current_car = make_car(odometer_km=55_000)

    historical_condition = ConditionRecord.empty(historical_car.car_id)
    current_condition = ConditionRecord.empty(current_car.car_id)
    current_condition.repairs.append(
        Repair(
            observed_at=datetime(2026, 9, 20, tzinfo=timezone.utc).date(),
            odometer_km=54_000,
            category="Brakes",
            description="Front brake service",
            cost_inr=5000,
            garage_type="Authorized",
        )
    )

    result = reconcile_vehicle_history(
        current_car,
        current_condition,
        [make_item(historical_car, historical_condition)],
    )

    assert result.status == "CHANGED"
    finding = next(item for item in result.findings if item.field == "repairs")
    assert finding.kind == "CHANGED"


def test_history_reconciliation_ignores_unstructured_memory():
    car = make_car()
    condition = ConditionRecord.empty(car.car_id)
    item = MemoryItem(
        memory_id="memory-unstructured",
        text="Seller said the car was always maintained well.",
        metadata={},
        tags=[f"vehicle:{car.car_id}"],
    )

    result = reconcile_vehicle_history(car, condition, [item])

    assert result.status == "NO_HISTORY"
    assert result.snapshots == ()
    assert result.ignored_items == 1


def test_history_reconciliation_does_not_treat_unknown_as_conflict():
    historical_car = make_car()
    current_car = make_car()
    historical_condition = ConditionRecord.empty(historical_car.car_id)
    historical_condition.accident_status = "Yes"

    current_condition = ConditionRecord.empty(current_car.car_id)

    result = reconcile_vehicle_history(
        current_car,
        current_condition,
        [make_item(historical_car, historical_condition)],
    )

    assert result.status == "MATCHED"
    assert not any(
        finding.field == "accident_status" for finding in result.findings
    )
