from core.condition import ConditionRecord
from core.database import Database
from core.memory_sync import sync_condition_to_memory
from core.models import Car


def test_memory_sync_records_failure_without_losing_local_data(tmp_path, monkeypatch):
    db = Database(tmp_path / "vericar.db")
    car = Car(car_id="CAR-1", brand="Toyota", model="City", manufacture_year=2020)
    condition = ConditionRecord.empty(car.car_id)
    db.save_car(car)

    class BrokenMemory:
        async def retain_vehicle_report(self, **kwargs):
            raise RuntimeError("Hindsight unavailable")

    monkeypatch.setattr("core.memory_sync.HindsightMemory", BrokenMemory)
    report_id, error = sync_condition_to_memory(car, condition, db)

    assert report_id.startswith("RPT-")
    assert error == "RuntimeError: Hindsight service unavailable."
    row = db.get_memory_report(report_id)
    assert row["status"] == "failed"
    assert row["error"] == "RuntimeError: Hindsight service unavailable."
    assert "CAR-1" not in row["error"]


def test_memory_sync_is_idempotent_for_identical_evidence(tmp_path, monkeypatch):
    db = Database(tmp_path / "vericar.db")
    car = Car(car_id="CAR-2", brand="Toyota", model="City", manufacture_year=2020)
    condition = ConditionRecord.empty(car.car_id)
    db.save_car(car)

    calls = []

    class FakeMemory:
        async def retain_vehicle_report(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr("core.memory_sync.HindsightMemory", FakeMemory)

    first_id, first_error = sync_condition_to_memory(car, condition, db)
    second_id, second_error = sync_condition_to_memory(car, condition, db)

    assert first_id == second_id
    assert first_error is None
    assert second_error is None
    assert len(calls) == 1
