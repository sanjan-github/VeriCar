from core.condition import ConditionRecord
from core.database import Database
from core.memory_sync import sync_condition_to_memory
from core.models import Car


def test_memory_sync_records_failure_without_losing_local_data(tmp_path, monkeypatch):
    db = Database(tmp_path / "vericar.db")
    car = Car(car_id="CAR-1", brand="Toyota", model="City", manufacture_year=2020)
    condition = ConditionRecord.empty(car.car_id)

    class BrokenMemory:
        async def retain_vehicle_report(self, **kwargs):
            raise RuntimeError("Hindsight unavailable")

    monkeypatch.setattr("core.memory_sync.HindsightMemory", BrokenMemory)
    report_id, error = sync_condition_to_memory(car, condition, db)

    assert report_id.startswith("RPT-")
    assert error == "Hindsight unavailable"
    row = db.get_memory_report(report_id)
    assert row["status"] == "failed"
    assert "Hindsight unavailable" in row["error"]
