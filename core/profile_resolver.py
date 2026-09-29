from __future__ import annotations

from dataclasses import dataclass

from core.database import Database
from core.expected_profile import ExpectedProfile
from core.models import Car


@dataclass(frozen=True)
class ProfileResolution:
    """Result of resolving a car against the local expected-profile store."""

    status: str
    profile_key: str
    profile: ExpectedProfile | None = None


def profile_key_for_car(car: Car) -> str:
    """Build the canonical expected-profile key for a vehicle."""
    return "|".join(
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


def resolve_expected_profile(car: Car, db: Database) -> ProfileResolution:
    """Resolve a locally stored expected profile without inventing fallback data."""
    key = profile_key_for_car(car)
    profile = db.get_expected_profile(key)
    if profile is None:
        return ProfileResolution(status="MISSING", profile_key=key)
    return ProfileResolution(status="FOUND", profile_key=key, profile=profile)
