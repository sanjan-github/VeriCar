from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from core.assessment import Assessment, assess_vehicle
from core.assessment_explanation import (
    AssessmentExplanation,
    generate_assessment_explanation,
)
from core.comparison import ComparisonFinding, compare_expected_vs_actual
from core.condition import ConditionRecord
from core.database import Database
from core.groq_llm import GroqLLM
from core.history_reconciliation import HistoryReconciliation, reconcile_vehicle_history
from memory.hindsight import MemoryItem
from core.models import Car
from core.profile_resolver import ProfileResolution, resolve_expected_profile
from core.profile_seed import seed_expected_profiles
from core.rules import RuleFlag, evaluate_rules


@dataclass(frozen=True)
class AssessmentPipelineResult:
    profile_resolution: ProfileResolution
    rule_flags: tuple[RuleFlag, ...]
    comparison_findings: tuple[ComparisonFinding, ...]
    assessment: Assessment | None
    explanation: AssessmentExplanation | None = None
    history_reconciliation: HistoryReconciliation | None = None


def run_assessment(
    car: Car,
    condition: ConditionRecord,
    db: Database,
    *,
    today: date | None = None,
    seed_missing_profiles: bool = True,
    generate_explanation: bool = False,
    llm: GroqLLM | None = None,
    history_items: list[MemoryItem] | tuple[MemoryItem, ...] | None = None,
) -> AssessmentPipelineResult:
    """Run the deterministic assessment pipeline for one vehicle.

    A missing expected profile prevents a verdict. No profile facts are invented.

    The optional LLM explanation runs only after the deterministic assessment
    has been produced and never changes that assessment.
    """
    if seed_missing_profiles:
        seed_expected_profiles(db)

    resolution = resolve_expected_profile(car, db)
    history_reconciliation = None
    if history_items is not None:
        history_reconciliation = reconcile_vehicle_history(car, condition, history_items)
    rule_flags = tuple(evaluate_rules(car, condition, today=today))

    if resolution.profile is None:
        return AssessmentPipelineResult(
            resolution,
            rule_flags,
            (),
            None,
            None,
            history_reconciliation,
        )

    comparison = tuple(
        compare_expected_vs_actual(car, condition, resolution.profile, today=today)
    )
    assessment = assess_vehicle(car, condition, list(rule_flags), list(comparison))

    explanation = None
    if generate_explanation:
        explanation = generate_assessment_explanation(
            car,
            condition,
            resolution.profile,
            assessment,
            rule_flags,
            comparison,
            llm=llm,
        )

    return AssessmentPipelineResult(
        resolution,
        rule_flags,
        comparison,
        assessment,
        explanation,
        history_reconciliation,
    )
