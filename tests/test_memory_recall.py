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
    assert result.error == "RuntimeError: Hindsight service unavailable."\n    assert "CAR-1" not in result.error


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


def test_memory_recall_deduplicates_cosmetic_hindsight_repeats(monkeypatch):
    async def fake_recall(self, *, vehicle_id, query):
        return [
            MemoryItem(memory_id="1", text="The vehicle is a 2022 Tata Nexon XZ+ with a petrol engine and manual transmission.", metadata={}, tags=[]),
            MemoryItem(memory_id="2", text="Vehicle is a 2022 Tata Nexon XZ+ with a petrol engine and manual transmission.", metadata={}, tags=[]),
            MemoryItem(memory_id="3", text="Vehicle has an odometer reading of 90,000 km and an asking price of 850,000 INR. | When: 2026-10-01", metadata={}, tags=[]),
            MemoryItem(memory_id="4", text="Vehicle has an odometer reading of 90,000 km and an asking price of 850,000 INR. | When: 2026-09-29", metadata={}, tags=[]),
        ]

    monkeypatch.setattr("core.memory_recall.HindsightMemory.recall_vehicle", fake_recall)

    result = recall_vehicle_memory(make_car(), query="vehicle history")

    assert result.status == "AVAILABLE"
    assert len(result.items) == 2
    assert {item.memory_id for item in result.items} == {"1", "3"}
