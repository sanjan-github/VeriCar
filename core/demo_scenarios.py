from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.condition import ConditionRecord, Repair, Service
from core.models import Car


@dataclass(frozen=True)
class DemoScenario:
    key: str
    name: str
    description: str
    car: Car
    condition: ConditionRecord


def _complete_condition(car_id: str) -> ConditionRecord:
    condition = ConditionRecord.empty(car_id)
    condition.documents = {key: "Yes" for key in condition.documents}
    condition.physical_inspection = {key: "No" for key in condition.physical_inspection}
    condition.test_drive = {key: "No" for key in condition.test_drive}
    condition.accident_status = "No"
    condition.repainted_panels = "No"
    condition.airbag_deployed = "No"
    return condition


def _base_nexon(car_id: str, odometer_km: int) -> Car:
    return Car(
        car_id=car_id,
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
        variant="XZ+",
        fuel_type="Petrol",
        transmission="Manual",
        manufacture_month=6,
        registration_date=date(2022, 7, 1),
        previous_owners=1,
        odometer_km=odometer_km,
        asking_price_inr=850_000,
    )


def build_demo_scenarios() -> tuple[DemoScenario, ...]:
    clean_car = _base_nexon("DEMO-CLEAN", 45_000)
    clean = _complete_condition(clean_car.car_id)
    clean.services = [
        Service(date(2025, 1, 15), 32_000, "Scheduled annual service"),
        Service(date(2026, 1, 15), 42_000, "Scheduled annual service"),
    ]

    negotiation_car = _base_nexon("DEMO-NEGOTIATE", 90_000)
    negotiation = _complete_condition(negotiation_car.car_id)
    negotiation.services = [
        Service(date(2023, 1, 15), 18_000, "Scheduled service"),
        Service(date(2025, 1, 15), 55_000, "Late scheduled service"),
        Service(date(2026, 1, 15), 82_000, "Scheduled service"),
    ]
    negotiation.repairs = [
        Repair(date(2024, 2, 1), 48_000, "Engine", "Engine mount replacement", 12_000, "Independent"),
        Repair(date(2025, 2, 1), 68_000, "Engine", "Engine mount replacement again", 14_000, "Independent"),
    ]

    critical_car = _base_nexon("DEMO-CRITICAL", 52_000)
    critical = _complete_condition(critical_car.car_id)
    critical.documents["vin_matches_rc"] = "No"
    critical.services = [
        Service(date(2025, 1, 15), 38_000, "Scheduled annual service"),
        Service(date(2026, 1, 15), 48_000, "Scheduled annual service"),
    ]

    return (
        DemoScenario(
            key="clean",
            name="Clean history",
            description="Complete synthetic evidence with regular service records and no critical findings.",
            car=clean_car,
            condition=clean,
        ),
        DemoScenario(
            key="negotiate",
            name="Negotiation case",
            description="Synthetic mileage, service-gap, and recurring-repair evidence producing multiple warnings.",
            car=negotiation_car,
            condition=negotiation,
        ),
        DemoScenario(
            key="critical",
            name="Critical-risk case",
            description="Synthetic document evidence containing a VIN/RC mismatch.",
            car=critical_car,
            condition=critical,
        ),
    )


def get_demo_scenario(key: str) -> DemoScenario:
    for scenario in build_demo_scenarios():
        if scenario.key == key:
            return scenario
    raise ValueError(f"Unknown demo scenario: {key!r}")
