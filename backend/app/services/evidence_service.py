from __future__ import annotations

from math import exp

from backend.app.models.evidence import (
    Assessment,
    EvidenceContribution,
    EvidenceRecord,
    EvidenceState,
    SourceHistory,
)


SOURCE_PRIORS: dict[str, float] = {
    "owner": 0.35,
    "buyer": 0.55,
    "mechanic": 0.75,
    "inspector": 0.85,
}

ALPHA = 4.0
BETA = 1.0
RELIABILITY_HISTORY_SCALE = 5.0
SUFFICIENCY_SCALE = 1.5

# These are product thresholds, not statistical significance thresholds.
CONFIDENCE_THRESHOLDS = {
    "limited_evidence": 25.0,
    "moderate_evidence": 50.0,
    "strong_evidence": 75.0,
}


class EvidenceService:
    """Deterministic evidence classification and confidence calculation."""

    def source_prior(self, source_type: str) -> float:
        if source_type not in SOURCE_PRIORS:
            raise ValueError(f"Unsupported source type: {source_type}")
        return SOURCE_PRIORS[source_type]

    def historical_reliability(self, history: SourceHistory) -> float:
        if history.resolved_reports < 0 or history.corroborated < 0 or history.contradicted < 0:
            raise ValueError("Source history counts cannot be negative")
        if history.corroborated + history.contradicted > history.resolved_reports:
            raise ValueError("Resolved reports cannot be less than outcomes")
        return (
            ALPHA + history.corroborated
        ) / (
            ALPHA + BETA + history.resolved_reports
        )

    def effective_reliability(
        self,
        source_type: str,
        history: SourceHistory | None = None,
    ) -> float:
        prior = self.source_prior(source_type)
        if history is None or history.resolved_reports == 0:
            return prior

        historical = self.historical_reliability(history)
        resolved = history.resolved_reports
        lam = resolved / (resolved + RELIABILITY_HISTORY_SCALE)
        return (1.0 - lam) * prior + lam * historical

    @staticmethod
    def _is_independent(record: EvidenceRecord, selected_sources: set[str], selected_dependencies: set[str]) -> bool:
        if record.source_id in selected_sources:
            return False
        if record.dependency_group is not None and record.dependency_group in selected_dependencies:
            return False
        return True

    def classify(
        self,
        issue_key: str,
        evidence: list[EvidenceRecord],
    ) -> Assessment:
        relevant = [item for item in evidence if item.issue_key == issue_key]
        relevant.sort(key=lambda item: (item.observed_at, item.evidence_id))

        supporting: list[EvidenceContribution] = []
        contradicting: list[EvidenceContribution] = []
        unresolved: list[EvidenceContribution] = []
        selected_support_sources: set[str] = set()
        selected_contra_sources: set[str] = set()
        selected_support_dependencies: set[str] = set()
        selected_contra_dependencies: set[str] = set()

        for item in relevant:
            contribution = EvidenceContribution(
                evidence_id=item.evidence_id,
                source_id=item.source_id,
                source_type=item.source_type,
                polarity=item.polarity,
                effective_reliability=self.effective_reliability(
                    item.source_type,
                    item.source_history,
                ),
                observed_at=item.observed_at,
                text=item.text,
            )
            if item.polarity == "unresolved":
                unresolved.append(contribution)
                continue

            if item.polarity == "supporting":
                if self._is_independent(item, selected_support_sources, selected_support_dependencies):
                    supporting.append(contribution)
                    selected_support_sources.add(item.source_id)
                    if item.dependency_group is not None:
                        selected_support_dependencies.add(item.dependency_group)
                continue

            if item.polarity == "contradicting":
                if self._is_independent(item, selected_contra_sources, selected_contra_dependencies):
                    contradicting.append(contribution)
                    selected_contra_sources.add(item.source_id)
                    if item.dependency_group is not None:
                        selected_contra_dependencies.add(item.dependency_group)

        support_weight = sum(item.effective_reliability for item in supporting)
        contradiction_weight = sum(item.effective_reliability for item in contradicting)
        total_weight = support_weight + contradiction_weight

        if total_weight == 0:
            confidence = None
            state: EvidenceState = "insufficient_evidence"
        else:
            direction = support_weight / total_weight
            sufficiency = 1.0 - exp(-total_weight / SUFFICIENCY_SCALE)
            confidence = 100.0 * direction * sufficiency
            state = self._state_for(confidence)

        return Assessment(
            issue_key=issue_key,
            state=state,
            confidence=None if confidence is None else round(confidence, 2),
            support_weight=round(support_weight, 6),
            contradiction_weight=round(contradiction_weight, 6),
            independent_supporting_sources=len(supporting),
            independent_contradicting_sources=len(contradicting),
            supporting_evidence=tuple(supporting),
            contradicting_evidence=tuple(contradicting),
            unresolved_evidence=tuple(unresolved),
        )

    @staticmethod
    def _state_for(confidence: float) -> EvidenceState:
        if confidence < CONFIDENCE_THRESHOLDS["limited_evidence"]:
            return "insufficient_evidence"
        if confidence < CONFIDENCE_THRESHOLDS["moderate_evidence"]:
            return "limited_evidence"
        if confidence < CONFIDENCE_THRESHOLDS["strong_evidence"]:
            return "moderate_evidence"
        return "strong_evidence"
