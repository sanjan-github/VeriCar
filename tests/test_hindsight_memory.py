from datetime import datetime, timezone

import pytest

from memory.hindsight import HindsightMemory


class FakeHindsight:
    def __init__(self) -> None:
        self.calls = []

    async def acreate_bank(self, **kwargs):
        self.calls.append(("create_bank", kwargs))

    async def aretain(self, **kwargs):
        self.calls.append(("retain", kwargs))
        return {"ok": True}

    async def arecall(self, **kwargs):
        self.calls.append(("recall", kwargs))
        return {
            "results": [
                {
                    "id": "memory-1",
                    "text": "Transmission hesitation reported.",
                    "metadata": {"source_id": "SRC-1"},
                    "tags": ["vehicle:CAR-1"],
                }
            ]
        }

    async def aclose(self):
        self.calls.append(("close", {}))


@pytest.mark.asyncio
async def test_retain_vehicle_report_creates_bank_and_stable_document():
    fake = FakeHindsight()
    memory = HindsightMemory(fake)
    observed_at = datetime(2026, 9, 20, 10, 0, tzinfo=timezone.utc)

    await memory.retain_vehicle_report(
        vehicle_id="CAR-1",
        report_id="RPT-1",
        text="Transmission hesitation reported.",
        observed_at=observed_at,
        metadata={"source_id": "SRC-1", "source_type": "mechanic"},
    )

    create_name, create_kwargs = fake.calls[0]
    retain_name, retain_kwargs = fake.calls[1]

    assert create_name == "create_bank"
    assert create_kwargs["bank_id"] == "vehicle_CAR-1"
    assert retain_name == "retain"
    assert retain_kwargs["bank_id"] == "vehicle_CAR-1"
    assert retain_kwargs["document_id"] == "report_RPT-1"
    assert retain_kwargs["timestamp"] == observed_at
    assert retain_kwargs["metadata"]["vehicle_id"] == "CAR-1"
    assert retain_kwargs["metadata"]["report_id"] == "RPT-1"
    assert "vehicle:CAR-1" in retain_kwargs["tags"]
    assert retain_kwargs["retain_async"] is False


@pytest.mark.asyncio
async def test_recall_vehicle_normalizes_memory_items():
    fake = FakeHindsight()
    memory = HindsightMemory(fake)

    items = await memory.recall_vehicle(
        vehicle_id="CAR-1",
        query="transmission history",
    )

    assert len(items) == 1
    assert items[0].memory_id == "memory-1"
    assert items[0].text == "Transmission hesitation reported."
    assert items[0].metadata["source_id"] == "SRC-1"

    recall_name, recall_kwargs = fake.calls[0]
    assert recall_name == "recall"
    assert recall_kwargs["bank_id"] == "vehicle_CAR-1"
    assert recall_kwargs["query"] == "transmission history"
    assert recall_kwargs["include_source_facts"] is True
    assert recall_kwargs["prefer_observations"] is True
    assert recall_kwargs["tags"] == ["vehicle:CAR-1"]


@pytest.mark.asyncio
async def test_empty_report_is_rejected_before_hindsight_call():
    fake = FakeHindsight()
    memory = HindsightMemory(fake)

    with pytest.raises(ValueError, match="report text"):
        await memory.retain_vehicle_report(
            vehicle_id="CAR-1",
            report_id="RPT-1",
            text="   ",
            observed_at=datetime.now(timezone.utc),
        )

    assert fake.calls == []


@pytest.mark.asyncio
async def test_empty_query_is_rejected_before_hindsight_call():
    fake = FakeHindsight()
    memory = HindsightMemory(fake)

    with pytest.raises(ValueError, match="query"):
        await memory.recall_vehicle(vehicle_id="CAR-1", query=" ")

    assert fake.calls == []
