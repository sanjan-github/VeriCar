from __future__ import annotations

import json
from datetime import date, datetime
from typing import Any

import pytest

from core.condition import ConditionRecord
from core.history_reconciliation import reconcile_vehicle_history
from core.models import Car
from memory.hindsight import MemoryItem


def _make_item(report_id: str, observed_at: str, odometer: int, repairs: int = 0) -> MemoryItem:
    car = Car(
        car_id="CAR123",
        brand="Toyota",
        model="Camry",
        manufacture_year=2015,
        variant=None,
        fuel_type="Petrol",
        transmission="Automatic",
        manufacture_month=None,
        registration_date=None,
        purchase_date=None,
        vin=None,
        registration_state=None,
        previous_owners=None,
        odometer_km=odometer,
        asking_price_inr=None,
    )
    cond = ConditionRecord.empty("CAR123")
    for i in range(repairs):
        from core.condition import Repair
        cond.repairs.append(
            Repair(
                observed_at=date.fromisoformat(observed_at[:10]),
                odometer_km=odometer,
                category="Engine",
                description=f"Fix {i}",
                cost_inr=1000,
                garage_type="Authorized",
            )
        )
    payload = {
        "vehicle": car.to_record(),
        "condition": cond.to_record(),
    }
    
    text = f"VeriCar vehicle evidence report.\n{json.dumps(payload)}"
    return MemoryItem(
        memory_id=f"mem-{report_id}",
        text=text,
        tags=[],
        metadata={
            "report_id": report_id,
            "observed_at": observed_at,
            "source_reliability": "verified",
            "evidence_confidence": "high",
        }
    )


def test_longitudinal_odometer_rollback():
    items = [
        _make_item("r1", "2023-01-01T10:00:00", 80000),
        _make_item("r2", "2023-06-01T10:00:00", 84000),
        _make_item("r3", "2024-01-01T10:00:00", 88000),
    ]
    
    car = Car(
        car_id="CAR123",
        brand="Toyota",
        model="Camry",
        manufacture_year=2015,
        variant=None,
        fuel_type="Petrol",
        transmission="Automatic",
        manufacture_month=None,
        registration_date=None,
        purchase_date=None,
        vin=None,
        registration_state=None,
        previous_owners=None,
        odometer_km=76000,
        asking_price_inr=None,
    )
    cond = ConditionRecord.empty("CAR123")
    
    recon = reconcile_vehicle_history(car, cond, items)
    assert recon.status == "CONTRADICTION"
    
    # We should have an influential memory related to contradiction
    contradicting = [im for im in recon.influential_memories if im.relevance == "historical contradiction"]
    assert len(contradicting) > 0
    assert any("76000" in im.reason or "88000" in im.reason for im in contradicting)


def test_longitudinal_repair_tracking():
    items = [
        _make_item("r1", "2023-01-01T10:00:00", 80000, repairs=1),
        _make_item("r2", "2023-06-01T10:00:00", 84000, repairs=2),
    ]
    
    car = Car(
        car_id="CAR123",
        brand="Toyota",
        model="Camry",
        manufacture_year=2015,
        variant=None,
        fuel_type="Petrol",
        transmission="Automatic",
        manufacture_month=None,
        registration_date=None,
        purchase_date=None,
        vin=None,
        registration_state=None,
        previous_owners=None,
        odometer_km=90000,
        asking_price_inr=None,
    )
    cond = ConditionRecord.empty("CAR123")
    
    # Let's say current has 0 repairs
    recon = reconcile_vehicle_history(car, cond, items)
    
    # Should flag a change/contradiction because repairs went down or didn't match
    assert recon.status == "CHANGED"
    assert any(im.field == "repairs" and im.relevance == "historical context" for im in recon.influential_memories)
