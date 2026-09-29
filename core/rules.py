from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Literal

from core.condition import ConditionRecord, Repair, Service
from core.models import Car, UNKNOWN


Severity = Literal["info", "warn", "critical"]


@dataclass(frozen=True)
class RuleFlag:
    """A deterministic finding produced from structured vehicle evidence."""

    rule: str
    severity: Severity
    message: str
    evidence: tuple[str, ...] = ()


# These are product defaults, not statistical claims. They are configurable
# inputs to the rules engine and should not be presented as probabilities.
DEFAULT_ANNUAL_KM_LOW = 8_000
DEFAULT_ANNUAL_KM_HIGH = 15_000
ODOMETER_DEVIATION_FACTOR = 0.5
SERVICE_INTERVAL_MONTHS = 12
SERVICE_GAP_GRACE_MONTHS = 3


def _years_since_reference(reference: date, today: date) -> float:
    days = max((today - reference).days, 0)
    return days / 365.25


def check_odometer_vs_age(
    car: Car,
    *,
    today: date | None = None,
    annual_km_low: int = DEFAULT_ANNUAL_KM_LOW,
    annual_km_high: int = DEFAULT_ANNUAL_KM_HIGH,
) -> list[RuleFlag]:
    """Flag an odometer materially outside a configurable annual-km range.

    The manufacture date is used when the month is known; otherwise July is
    used as a neutral midpoint for the manufacture year. Missing odometer
    data produces an informational flag rather than an error.
    """

    if car.odometer_km is None:
        return [
            RuleFlag(
                "odometer_vs_age",
                "info",
                "Current odometer is unknown; mileage-versus-age cannot be assessed.",
            )
        ]

    today = today or date.today()
    month = car.manufacture_month or 7
    try:
        manufacture_date = date(car.manufacture_year, month, 15)
    except ValueError:
        return [
            RuleFlag(
                "odometer_vs_age",
                "info",
                "Manufacture date is incomplete; mileage-versus-age cannot be assessed.",
            )
        ]

    years = _years_since_reference(manufacture_date, today)
    if years <= 0:
        return []

    expected_low = annual_km_low * years
    expected_high = annual_km_high * years

    if car.odometer_km < expected_low * ODOMETER_DEVIATION_FACTOR:
        return [
            RuleFlag(
                "odometer_vs_age",
                "warn",
                (
                    f"Recorded odometer ({car.odometer_km:,} km) is materially below "
                    f"the configured age-based range ({expected_low:,.0f}–{expected_high:,.0f} km)."
                ),
                (f"odometer={car.odometer_km}", f"expected_low={expected_low:.0f}"),
            )
        ]

    if car.odometer_km > expected_high * (1 / ODOMETER_DEVIATION_FACTOR):
        return [
            RuleFlag(
                "odometer_vs_age",
                "warn",
                (
                    f"Recorded odometer ({car.odometer_km:,} km) is materially above "
                    f"the configured age-based range ({expected_low:,.0f}–{expected_high:,.0f} km)."
                ),
                (f"odometer={car.odometer_km}", f"expected_high={expected_high:.0f}"),
            )
        ]

    return []


def check_service_odometer_order(
    car: Car,
    services: list[Service],
) -> list[RuleFlag]:
    if car.odometer_km is None:
        return [
            RuleFlag(
                "service_odometer_order",
                "info",
                "Current odometer is unknown; service-log odometer consistency cannot be fully checked.",
            )
        ]

    flags: list[RuleFlag] = []
    for index, service in enumerate(services, start=1):
        if service.odometer_km is not None and service.odometer_km > car.odometer_km:
            flags.append(
                RuleFlag(
                    "service_odometer_order",
                    "critical",
                    (
                        f"Service {index} records {service.odometer_km:,} km, which exceeds "
                        f"the current odometer of {car.odometer_km:,} km."
                    ),
                    (f"service_{index}_odometer={service.odometer_km}", f"current_odometer={car.odometer_km}"),
                )
            )
    return flags


def check_service_gaps(
    services: list[Service],
    *,
    today: date | None = None,
    expected_interval_months: int = SERVICE_INTERVAL_MONTHS,
    grace_months: int = SERVICE_GAP_GRACE_MONTHS,
) -> list[RuleFlag]:
    """Flag recorded service intervals that materially exceed the configured interval."""

    if not services:
        return [
            RuleFlag(
                "service_gaps",
                "info",
                "No service records are available; service continuity cannot be assessed.",
            )
        ]

    today = today or date.today()
    ordered = sorted(services, key=lambda item: item.observed_at)
    flags: list[RuleFlag] = []

    for previous, current in zip(ordered, ordered[1:]):
        months = (current.observed_at.year - previous.observed_at.year) * 12 + (
            current.observed_at.month - previous.observed_at.month
        )
        if months > expected_interval_months + grace_months:
            flags.append(
                RuleFlag(
                    "service_gaps",
                    "warn",
                    (
                        f"Service interval from {previous.observed_at.isoformat()} to "
                        f"{current.observed_at.isoformat()} is about {months} months, "
                        f"above the configured {expected_interval_months}-month interval "
                        f"plus {grace_months}-month grace."
                    ),
                    (previous.observed_at.isoformat(), current.observed_at.isoformat()),
                )
            )

    last_service_months = (
        (today.year - ordered[-1].observed_at.year) * 12
        + today.month
        - ordered[-1].observed_at.month
    )
    if last_service_months > expected_interval_months + grace_months:
        flags.append(
            RuleFlag(
                "service_gaps",
                "warn",
                (
                    f"The latest recorded service is about {last_service_months} months old, "
                    f"above the configured {expected_interval_months}-month interval "
                    f"plus {grace_months}-month grace."
                ),
                (ordered[-1].observed_at.isoformat(), today.isoformat()),
            )
        )

    return flags


def check_recurring_repairs(
    repairs: list[Repair],
    *,
    window_days: int = 730,
) -> list[RuleFlag]:
    """Flag categories repaired at least twice within a rolling two-year window."""

    ordered = sorted(repairs, key=lambda item: item.observed_at)
    flags: list[RuleFlag] = []

    for category in sorted({item.category for item in ordered}):
        category_repairs = [
            item for item in ordered if item.category == category
        ]
        for start_index, first in enumerate(category_repairs):
            window = [
                item
                for item in category_repairs[start_index:]
                if (item.observed_at - first.observed_at).days <= window_days
            ]
            if len(window) >= 2:
                flags.append(
                    RuleFlag(
                        "recurring_repair",
                        "warn",
                        (
                            f"{category} was repaired {len(window)} times within "
                            f"{window_days // 365} years."
                        ),
                        tuple(item.observed_at.isoformat() for item in window),
                    )
                )
                break

    return flags


def check_flood_indicators(condition: ConditionRecord) -> list[RuleFlag]:
    flood_keys = {
        "flood_signs": condition.physical_inspection.get("flood_signs", UNKNOWN),
        "rust": condition.physical_inspection.get("rust", UNKNOWN),
        "battery_corrosion": condition.physical_inspection.get("battery_corrosion", UNKNOWN),
        "wear_mismatch": condition.physical_inspection.get("wear_mismatch", UNKNOWN),
    }
    positive = [key for key, value in flood_keys.items() if value == "Yes"]

    if len(positive) >= 2:
        return [
            RuleFlag(
                "flood_indicators",
                "critical",
                f"{len(positive)} flood-related inspection indicators were marked Yes.",
                tuple(positive),
            )
        ]

    if positive:
        return [
            RuleFlag(
                "flood_indicators",
                "warn",
                "One flood-related inspection indicator was marked Yes; additional evidence is needed.",
                tuple(positive),
            )
        ]

    return []


def check_vin_rc_match(condition: ConditionRecord) -> list[RuleFlag]:
    value = condition.documents.get("vin_matches_rc", UNKNOWN)

    if value == "No":
        return [
            RuleFlag(
                "vin_rc_match",
                "critical",
                "VIN/chassis number does not match the RC record.",
                ("vin_matches_rc=No",),
            )
        ]

    if value == UNKNOWN:
        return [
            RuleFlag(
                "vin_rc_match",
                "info",
                "VIN/chassis-to-RC match is unknown.",
                ("vin_matches_rc=Unknown",),
            )
        ]

    return []


def count_unknowns(condition: ConditionRecord) -> int:
    return sum(
        value == UNKNOWN
        for values in (
            condition.documents,
            condition.physical_inspection,
            condition.test_drive,
        )
        for value in values.values()
    )


def evaluate_rules(
    car: Car,
    condition: ConditionRecord,
    *,
    today: date | None = None,
) -> list[RuleFlag]:
    """Run all currently implemented deterministic rules."""

    flags: list[RuleFlag] = []
    flags.extend(check_odometer_vs_age(car, today=today))
    flags.extend(check_service_odometer_order(car, condition.services))
    flags.extend(check_service_gaps(condition.services, today=today))
    flags.extend(check_recurring_repairs(condition.repairs))
    flags.extend(check_flood_indicators(condition))
    flags.extend(check_vin_rc_match(condition))

    unknowns = count_unknowns(condition)
    if unknowns:
        flags.append(
            RuleFlag(
                "unknown_data",
                "info",
                f"{unknowns} checklist values remain Unknown and should lower assessment confidence.",
                (f"unknown_checklist_items={unknowns}",),
            )
        )

    return flags
