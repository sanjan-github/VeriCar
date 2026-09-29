from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.assessment import Assessment
from core.comparison import ComparisonFinding
from core.condition import ConditionRecord
from core.expected_profile import ExpectedProfile
from core.groq_llm import GroqLLM, LLMExplanation
from core.models import Car
from core.rules import RuleFlag


@dataclass(frozen=True)
class AssessmentExplanation:
    llm: LLMExplanation


def build_explanation_evidence(
    car: Car,
    condition: ConditionRecord,
    profile: ExpectedProfile,
    assessment: Assessment,
    rule_flags: tuple[RuleFlag, ...],
    comparison_findings: tuple[ComparisonFinding, ...],
) -> dict[str, Any]:
    """Build explicit evidence for the LLM explanation layer.

    The deterministic assessment remains authoritative. This payload gives
    the LLM facts to explain; it does not ask the LLM to make the assessment.
    """
    return {
        "vehicle": car.to_record(),
        "expected_profile": profile.to_record(),
        "condition": condition.to_record(),
        "deterministic_assessment": {
            "verdict": assessment.verdict,
            "confidence": assessment.confidence,
            "near_term_repair_range_inr": assessment.near_term_repair_range_inr,
            "negotiation_reduction_inr": assessment.negotiation_reduction_inr,
            "next_checks": assessment.next_checks,
            "critical_findings": assessment.critical_findings,
            "warning_findings": assessment.warning_findings,
            "info_findings": assessment.info_findings,
        },
        "rule_flags": [
            {
                "rule": flag.rule,
                "severity": flag.severity,
                "message": flag.message,
                "evidence": flag.evidence,
            }
            for flag in rule_flags
        ],
        "comparison_findings": [
            {
                "category": finding.category,
                "severity": finding.severity,
                "message": finding.message,
                "evidence": finding.evidence,
            }
            for finding in comparison_findings
        ],
    }


def generate_assessment_explanation(
    car: Car,
    condition: ConditionRecord,
    profile: ExpectedProfile,
    assessment: Assessment,
    rule_flags: tuple[RuleFlag, ...],
    comparison_findings: tuple[ComparisonFinding, ...],
    *,
    llm: GroqLLM | None = None,
) -> AssessmentExplanation | None:
    """Generate an optional LLM explanation.

    Groq failure must never invalidate the deterministic assessment.
    """
    evidence = build_explanation_evidence(
        car,
        condition,
        profile,
        assessment,
        rule_flags,
        comparison_findings,
    )

    try:
        client = llm or GroqLLM.from_environment()
        explanation = client.explain(evidence)
    except RuntimeError:
        return None

    return AssessmentExplanation(llm=explanation)
