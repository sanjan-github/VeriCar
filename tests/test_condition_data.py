from datetime import date

from core.condition import ConditionRecord, Repair, Service
from core.database import Database


def test_condition_round_trip(tmp_path):
    database = Database(tmp_path / "vericar.db")

    from core.models import Car

    car = Car(
        car_id="CAR-TEST",
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
    )
    database.save_car(car)

    condition = ConditionRecord(
        car_id=car.car_id,
        repairs=[
            Repair(
                observed_at=date(2025, 4, 10),
                odometer_km=42000,
                category="Transmission",
                description="Clutch assembly replaced",
                cost_inr=28000,
                garage_type="Independent",
            )
        ],
        services=[
            Service(
                observed_at=date(2025, 1, 10),
                odometer_km=39000,
                description="Routine service",
                gap_notes="",
            )
        ],
        accident_status="No",
        documents={"vin_matches_rc": "Yes"},
        physical_inspection={"flood_signs": "Unknown"},
    )
    database.save_condition(condition)

    loaded = database.get_condition(car.car_id)

    assert loaded is not None
    assert loaded.repairs[0].category == "Transmission"
    assert loaded.repairs[0].cost_inr == 28000
    assert loaded.services[0].odometer_km == 39000
    assert loaded.accident_status == "No"
    assert loaded.physical_inspection["flood_signs"] == "Unknown"
