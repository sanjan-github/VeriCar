from __future__ import annotations

from dataclasses import dataclass
from typing import Any


UNKNOWN = "unknown"


def _key_part(value: str | int | None) -> str:
    if value is None:
        return UNKNOWN
    text = str(value).strip().lower()
    return text or UNKNOWN


@dataclass(frozen=True)
class ExpectedProfile:
    """Structured expectations for a vehicle configuration.

    These are reference facts/expectations, not observations about a specific car.
    """

    brand: str
    model: str
    manufacture_year: int
    variant: str | None
    fuel_type: str | None
    transmission: str | None
    expected_annual_km_low: int | None
    expected_annual_km_high: int | None
    service_interval_months: int | None
    known_issues: list[str]
    maintenance_notes: list[str]
    source: str

    @property
    def profile_key(self) -> str:
        return "|".join(
            _key_part(value)
            for value in (
                self.brand,
                self.model,
                self.manufacture_year,
                self.variant,
                self.fuel_type,
                self.transmission,
            )
        )

    def to_record(self) -> dict[str, Any]:
        return {
            "profile_key": self.profile_key,
            "brand": self.brand,
            "model": self.model,
            "manufacture_year": self.manufacture_year,
            "variant": self.variant,
            "fuel_type": self.fuel_type,
            "transmission": self.transmission,
            "expected_annual_km_low": self.expected_annual_km_low,
            "expected_annual_km_high": self.expected_annual_km_high,
            "service_interval_months": self.service_interval_months,
            "known_issues": list(self.known_issues),
            "maintenance_notes": list(self.maintenance_notes),
            "source": self.source,
        }

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ExpectedProfile":
        return cls(
            brand=record["brand"],
            model=record["model"],
            manufacture_year=int(record["manufacture_year"]),
            variant=record.get("variant"),
            fuel_type=record.get("fuel_type"),
            transmission=record.get("transmission"),
            expected_annual_km_low=record.get("expected_annual_km_low"),
            expected_annual_km_high=record.get("expected_annual_km_high"),
            service_interval_months=record.get("service_interval_months"),
            known_issues=list(record.get("known_issues", [])),
            maintenance_notes=list(record.get("maintenance_notes", [])),
            source=record["source"],
        )
