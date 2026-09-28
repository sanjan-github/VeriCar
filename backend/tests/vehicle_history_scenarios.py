"""Canonical synthetic vehicle-history scenarios for evidence regression tests."""

from dataclasses import dataclass
from datetime import date

from backend.app.models.evidence import EvidenceRecord, Polarity, SourceType
from backend.app.models.report import Claim


ISSUE = "transmission_shift_behavior"


@dataclass(frozen=True)
class ScenarioReport:
    report_id: str
    source_id: str
    source_type: SourceType
    observed_at: date
    text: str
    polarity: Polarity

    @property
    def claim(self) -> Claim:
        """The report's structured claim, kept distinct from scored evidence."""
        return Claim(
            claim_id=f"CLM-{self.report_id}",
            report_id=self.report_id,
            text=self.text,
            issue_candidate=ISSUE,
            polarity=self.polarity,
        )

    def to_evidence(self) -> EvidenceRecord:
        claim = self.claim
        return EvidenceRecord(
            evidence_id=self.report_id,
            issue_key=claim.issue_candidate or "unknown",
            source_id=self.source_id,
            source_type=self.source_type,
            polarity=claim.polarity,
            observed_at=self.observed_at,
            text=claim.text,
        )


@dataclass(frozen=True)
class VehicleHistoryScenario:
    scenario_id: str
    vehicle_id: str
    reports: tuple[ScenarioReport, ...]

    def evidence(self) -> list[EvidenceRecord]:
        return [report.to_evidence() for report in self.reports]


SCENARIOS = {
    "single_supporting": VehicleHistoryScenario(
        "single_supporting_001",
        "TEST-VEHICLE-101",
        (ScenarioReport("RPT-101-A", "SRC-MECH-101", "mechanic", date(2026, 1, 12),
                        "Hesitation occurred during the 2-to-3 shift.", "supporting"),),
    ),
    "independent_support": VehicleHistoryScenario(
        "corroboration_001",
        "TEST-VEHICLE-102",
        (
            ScenarioReport("RPT-102-A", "SRC-MECH-102", "mechanic", date(2026, 2, 10),
                           "Hesitation occurred during the 2-to-3 shift.", "supporting"),
            ScenarioReport("RPT-102-B", "SRC-INSP-102", "inspector", date(2026, 3, 20),
                           "Delayed engagement appeared during the road test.", "supporting"),
        ),
    ),
    "contradiction": VehicleHistoryScenario(
        "contradiction_001",
        "TEST-VEHICLE-103",
        (
            ScenarioReport("RPT-103-A", "SRC-OWNER-103", "owner", date(2026, 2, 1),
                           "Transmission operated normally with no hesitation.", "contradicting"),
            ScenarioReport("RPT-103-B", "SRC-MECH-103", "mechanic", date(2026, 3, 15),
                           "A hard shift appeared between second and third gear.", "supporting"),
        ),
    ),
    "same_source_repetition": VehicleHistoryScenario(
        "repetition_001",
        "TEST-VEHICLE-104",
        (
            ScenarioReport("RPT-104-A", "SRC-MECH-104", "mechanic", date(2026, 2, 1),
                           "Hesitation occurred during 2-to-3 shifting.", "supporting"),
            ScenarioReport("RPT-104-B", "SRC-MECH-104", "mechanic", date(2026, 2, 15),
                           "Hesitation continued during 2-to-3 shifting.", "supporting"),
        ),
    ),
    "unresolved": VehicleHistoryScenario(
        "unresolved_001",
        "TEST-VEHICLE-105",
        (ScenarioReport("RPT-105-A", "SRC-OWNER-105", "owner", date(2026, 4, 4),
                        "An occasional vibration was felt at highway speed.", "unresolved"),),
    ),
    "mixed_source_types": VehicleHistoryScenario(
        "multi_source_001",
        "TEST-VEHICLE-106",
        (
            ScenarioReport("RPT-106-A", "SRC-BUYER-106", "buyer", date(2026, 1, 10),
                           "Occasional shift hesitation was noticed.", "supporting"),
            ScenarioReport("RPT-106-B", "SRC-MECH-106", "mechanic", date(2026, 3, 5),
                           "Intermittent shift hesitation appeared on test drive.", "supporting"),
            ScenarioReport("RPT-106-C", "SRC-INSP-106", "inspector", date(2026, 5, 1),
                           "Delayed transmission engagement appeared during inspection.", "supporting"),
        ),
    ),
    "temporal_progression": VehicleHistoryScenario(
        "temporal_001",
        "TEST-VEHICLE-107",
        (
            ScenarioReport("RPT-107-A", "SRC-OWNER-107", "owner", date(2026, 1, 1),
                           "Transmission operated normally.", "contradicting"),
            ScenarioReport("RPT-107-B", "SRC-BUYER-107", "buyer", date(2026, 3, 1),
                           "Occasional hesitation was noticed.", "supporting"),
            ScenarioReport("RPT-107-C", "SRC-MECH-107", "mechanic", date(2026, 5, 1),
                           "A noticeable 2-to-3 shift hesitation appeared.", "supporting"),
        ),
    ),
    "insufficient_history": VehicleHistoryScenario(
        "insufficient_001", "TEST-VEHICLE-108", (),
    ),
}
