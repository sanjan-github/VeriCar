from core.memory_recall import recall_vehicle_memory
from core.models import Car
from memory.hindsight import MemoryItem


def make_car() -> Car:
    return Car(
        car_id="CAR-1",
        brand="Tata",
        model="Nexon",
        manufacture_year=2022,
    )


def test_memory_recall_returns_items(monkeypatch):
    class FakeMemory:
        def recall_vehicle(self, *, vehicle_id, query):
            raise AssertionError("sync wrapper must use asyncio.run")

    async def fake_recall(self, *, vehicle_id, query):
        assert vehicle_id == "CAR-1"
        assert query == "transmission history"
        return [
            MemoryItem(
                memory_id="memory-1",
                text="Transmission hesitation reported.",
                metadata={"source_id": "SRC-1"},
                tags=["vehicle:CAR-1"],
            )
        ]

    monkeypatch.setattr("core.memory_recall.HindsightMemory.recall_vehicle", fake_recall)

    result = recall_vehicle_memory(make_car(), query="transmission history")

    assert result.status == "AVAILABLE"
    assert len(result.items) == 1
    assert result.items[0].text == "Transmission hesitation reported."


def test_memory_recall_reports_service_unavailable(monkeypatch):
    async def fake_recall(self, *, vehicle_id, query):
        raise RuntimeError("connection refused")

    monkeypatch.setattr("core.memory_recall.HindsightMemory.recall_vehicle", fake_recall)

    result = recall_vehicle_memory(make_car(), query="vehicle history")

    assert result.status == "UNAVAILABLE"
    assert result.items == ()
    assert "connection refused" in result.error


def test_memory_recall_rejects_empty_query():
    import pytest

    with pytest.raises(ValueError, match="query"):
        recall_vehicle_memory(make_car(), query=" ")



def test_memory_recall_history_returns_original_reports(monkeypatch):
    async def fake_recall(self, *, vehicle_id, query):
        assert vehicle_id == "CAR-1"
        assert query == "vehicle evidence report"
        return [
            MemoryItem(
                memory_id="memory-report",
                text="VeriCar vehicle evidence report. {\"vehicle\": {}}",
                metadata={"report_id": "RPT-1"},
                tags=["vehicle:CAR-1"],
            )
        ]

    monkeypatch.setattr(
        "core.memory_recall.HindsightMemory.recall_vehicle_reports",
        fake_recall,
    )

    from core.memory_recall import recall_vehicle_history

    result = recall_vehicle_history(make_car())

    assert result.status == "AVAILABLE"
    assert len(result.items) == 1
    assert result.items[0].metadata["report_id"] == "RPT-1"
