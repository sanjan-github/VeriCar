from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.expected_profile import ExpectedProfile
from core.models import Car
from core.data_source import DataSource, ProviderResult


class VehicleProfileProvider(Protocol):
    """Contract for any provider that can supply a vehicle reference profile."""

    @property
    def source(self) -> DataSource:
        ...

    def get_profile(self, car: Car) -> ProviderResult:
        ...


@dataclass(frozen=True)
class SyntheticProfileProvider:
    """Adapter for the version-controlled synthetic reference profiles.

    This provider is deliberately local and deterministic. It is useful as a
    fallback/demo provider until verified external sources are integrated.
    """

    profiles: tuple[ExpectedProfile, ...]
    source: DataSource = DataSource(
        source_id="synthetic_seed",
        name="VeriCar synthetic reference profiles",
        kind="synthetic",
        description="Version-controlled synthetic data for development and demonstrations.",
    )

    def get_profile(self, car: Car) -> ProviderResult:
        key = "|".join(
            str(value).strip().lower() if value is not None and str(value).strip() else "unknown"
            for value in (
                car.brand,
                car.model,
                car.manufacture_year,
                car.variant,
                car.fuel_type,
                car.transmission,
            )
        )
        for profile in self.profiles:
            if profile.profile_key == key:
                return ProviderResult(
                    status="FOUND",
                    source=self.source,
                    data=profile,
                )
        return ProviderResult(
            status="NOT_FOUND",
            source=self.source,
            message=f"No synthetic profile exists for {key}.",
        )
