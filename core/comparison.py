from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.condition import ConditionRecord
from core.expected_profile import ExpectedProfile
from core.models import Car


@dataclass(frozen=True)
class ComparisonFinding:
    """A factual discrepancy or missing-evidence finding; not a verdict."""

    category: str
    severity: str
    message: str
    evidence: tuple[str, ...] = ()


def compare_expected_vs_actual(
    car: Car,
    condition: ConditionRecord,
    profile: ExpectedProfile,
    *,
    today: date | None = None,
) -> list[ComparisonFinding]:
    """Compare available evidence with the stored reference profile.

    This function does not produce BUY/NEGOTIATE/AVOID and does not infer
    facts that are absent from the condition record.
    """
    findings: list[ComparisonFinding] = []

    if car.odometer_km is not None:
        if profile.expected_annual_km_high is not None:
            year = (today or date.today()).year
            age = max(1, year - car.manufacture_year)
            expected_high = profile.expected_annual_km_high * age
            if car.odometer_km > expected_high:
                findings.append(
                    ComparisonFinding(
                        "mileage", "warn",
                        "Odometer is above the seeded expected annual-use range.",
                        (f"actual_odometer_km={car.odometer_km}", f"reference_upper_km={expected_high}"),
                    )
                )
    else:
        findings.append(ComparisonFinding("mileage", "unknown", "Odometer is unknown."))

    if condition.services:
        if profile.service_interval_months is not None:
            findings.append(
                ComparisonFinding(
                    "service", "info",
                    "Service history is available and can be checked against the reference interval.",
                    (f"reference_interval_months={profile.service_interval_months}", f"service_records={len(condition.services)}"),
                )
            )
    else:
        findings.append(ComparisonFinding("service", "unknown", "No service records were provided."))

    for issue in profile.known_issues:
        matching_repairs = [
            repair for repair in condition.repairs
            if issue.lower().split()[0] in repair.description.lower()
            or issue.lower().split()[0] in repair.category.lower()
        ]
        if matching_repairs:
            findings.append(
                ComparisonFinding(
                    "known_issue", "info",
                    f"Reference issue has related repair evidence: {issue}",
                    tuple(repair.description for repair in matching_repairs),
                )
            )

    if not condition.repairs:
        findings.append(ComparisonFinding("repairs", "unknown", "No repair records were provided."))

    if not findings:
        findings.append(ComparisonFinding("profile", "info", "No discrepancy was identified from the available comparison inputs."))

    return findings
