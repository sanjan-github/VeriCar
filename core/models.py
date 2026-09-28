from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from typing import Any
from uuid import uuid4


UNKNOWN = "Unknown"


@dataclass
class Car:
    """Editable vehicle setup data."""

    car_id: str
    brand: str
    model: str
    manufacture_year: int
    variant: str | None = None
    fuel_type: str | None = None
    transmission: str | None = None
    manufacture_month: int | None = None
    registration_date: date | None = None
    purchase_date: date | None = None
    vin: str | None = None
    registration_state: str | None = None
    previous_owners: int | None = None
    odometer_km: int | None = None
    asking_price_inr: int | None = None

    @property
    def memory_key(self) -> str:
        return self.vin.strip() if self.vin and self.vin.strip() else self.car_id

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        for field in ("registration_date", "purchase_date"):
            value = record[field]
            record[field] = value.isoformat() if value else None
        return record


def new_car_id() -> str:
    return f"CAR-{uuid4().hex[:10].upper()}"


def clean_optional_text(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None
