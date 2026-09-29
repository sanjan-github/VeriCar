from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.comparison import ComparisonFinding
from core.condition import ConditionRecord
from core.models import Car
from core.rules import RuleFlag

Verdict = Literal["BUY", "NEGOTIATE", "AVOID"]


@dataclass(frozen=True)
class Assessment:
    verdict: Verdict
    confidence: int
    near_term_repair_range_inr: tuple[int, int]
    negotiation_reduction_inr: int
    next_checks: tuple[str, ...]
    critical_findings: tuple[str, ...]
    warning_findings: tuple[str, ...]
    info_findings: tuple[str, ...]


def _repair_range(condition: ConditionRecord) -> tuple[int, int]:
    costs = [repair.cost_inr for repair in condition.repairs if repair.cost_inr is not None]
    if not costs:
        return (0, 0)
    total = sum(costs)
    return (total, int(round(total * 1.25)))


def assess_vehicle(
    car: Car,
    condition: ConditionRecord,
    rule_flags: list[RuleFlag],
    comparison_findings: list[ComparisonFinding],
) -> Assessment:
    """Produce a deterministic assessment from explicit evidence only."""
    critical = [f.message for f in rule_flags if f.severity == "critical"]
    warnings = [f.message for f in rule_flags if f.severity == "warn"]
    infos = [f.message for f in rule_flags if f.severity == "info"]
    warnings.extend(f.message for f in comparison_findings if f.severity == "warn")
    infos.extend(f.message for f in comparison_findings if f.severity == "info")

    unknown_count = sum(1 for f in rule_flags if f.rule == "unknown_data" for _ in range(1))
    unknown_count += sum(1 for f in comparison_findings if f.severity == "unknown")

    if critical:
        verdict: Verdict = "AVOID"
    elif len(warnings) >= 3:
        verdict = "NEGOTIATE"
    else:
        verdict = "BUY"

    confidence = 90
    confidence -= min(35, unknown_count * 5)
    confidence -= min(20, max(0, len(warnings) - 1) * 5)
    if critical:
        confidence = max(confidence, 75)
    confidence = max(25, min(95, confidence))

    repair_low, repair_high = _repair_range(condition)
    reduction = repair_high if verdict == "NEGOTIATE" else repair_low if verdict == "AVOID" else 0

    checks: list[str] = []
    if unknown_count:
        checks.append("Obtain the missing service, repair, document, and inspection evidence.")
    if not condition.services:
        checks.append("Request service invoices or service-record evidence.")
    if not condition.repairs:
        checks.append("Ask for repair invoices and accident/claim records.")
    if not checks:
        checks.append("Verify the key findings with an independent inspection and original documents.")

    return Assessment(
        verdict=verdict,
        confidence=confidence,
        near_term_repair_range_inr=(repair_low, repair_high),
        negotiation_reduction_inr=reduction,
        next_checks=tuple(dict.fromkeys(checks)),
        critical_findings=tuple(dict.fromkeys(critical)),
        warning_findings=tuple(dict.fromkeys(warnings)),
        info_findings=tuple(dict.fromkeys(infos)),
    )
