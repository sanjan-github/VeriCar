from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.assessment import Assessment, assess_vehicle
from core.comparison import ComparisonFinding, compare_expected_vs_actual
from core.condition import ConditionRecord
from core.database import Database
from core.expected_profile import ExpectedProfile
from core.profile_resolver import ProfileResolution, resolve_expected_profile
from core.profile_seed import seed_expected_profiles
from core.models import Car
from core.rules import RuleFlag, evaluate_rules


@dataclass(frozen=True)
class AssessmentPipelineResult:
    profile_resolution: ProfileResolution
    rule_flags: tuple[RuleFlag, ...]
    comparison_findings: tuple[ComparisonFinding, ...]
    assessment: Assessment | None


def run_assessment(
    car: Car,
    condition: ConditionRecord,
    db: Database,
    *,
    today: date | None = None,
    seed_missing_profiles: bool = True,
) -> AssessmentPipelineResult:
    """Run the deterministic assessment pipeline for one vehicle.

    A missing expected profile prevents a verdict. No profile facts are invented.
    """
    if seed_missing_profiles:
        seed_expected_profiles(db)

    resolution = resolve_expected_profile(car, db)
    rule_flags = tuple(evaluate_rules(car, condition, today=today))

    if resolution.profile is None:
        return AssessmentPipelineResult(resolution, rule_flags, (), None)

    comparison = tuple(
        compare_expected_vs_actual(car, condition, resolution.profile, today=today)
    )
    assessment = assess_vehicle(car, condition, list(rule_flags), list(comparison))
    return AssessmentPipelineResult(resolution, rule_flags, comparison, assessment)
