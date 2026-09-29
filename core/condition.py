from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

from core.models import UNKNOWN


REPAIR_CATEGORIES = (
    "Engine",
    "Transmission",
    "AC",
    "Electrical",
    "Suspension",
    "Brakes",
    "Body / accident",
    "Tyres",
    "Other",
)

GARAGE_TYPES = ("Authorized", "Independent", "Roadside", UNKNOWN)

YES_NO_UNKNOWN = ("Yes", "No", UNKNOWN)

DOCUMENT_FIELDS = {
    "rc_match": "RC matches vehicle details",
    "insurance_valid": "Insurance valid",
    "insurance_claim_history": "Insurance claim history known",
    "no_claim_bonus": "No-claim bonus known",
    "puc_valid": "PUC valid",
    "loan_hypothecation_closed": "Loan hypothecation closed",
    "form_29_30_available": "Form 29/30 available",
    "vin_matches_rc": "VIN/chassis matches RC",
}

PHYSICAL_FIELDS = {
    "panel_gaps_or_paint_mismatch": "Uneven panel gaps or paint mismatch",
    "rust": "Rust at wheel arches or underbody",
    "oil_or_coolant_leaks": "Oil or coolant leaks",
    "exhaust_smoke": "Exhaust smoke",
    "rough_idle": "Rough idle",
    "battery_corrosion": "Battery terminal corrosion",
    "ac_works": "AC works",
    "lights_windows_work": "Lights and windows work",
    "flood_signs": "Damp/musty smell or stained carpet (flood signs)",
    "wear_mismatch": "Pedal and steering wear does not match odometer",
}

TEST_DRIVE_FIELDS = {
    "engine_noise": "Unusual engine noise",
    "hesitation": "Hesitation",
    "brakes_pull_or_spongy": "Brakes pull to one side or feel spongy",
    "steering_play": "Steering play",
}


@dataclass
class Repair:
    observed_at: date
    odometer_km: int | None
    category: str
    description: str
    cost_inr: int | None
    garage_type: str


@dataclass
class Service:
    observed_at: date
    odometer_km: int | None
    description: str
    gap_notes: str | None = None


@dataclass
class ConditionRecord:
    car_id: str
    repairs: list[Repair] = field(default_factory=list)
    services: list[Service] = field(default_factory=list)
    accident_status: str = UNKNOWN
    repainted_panels: str = UNKNOWN
    airbag_deployed: str = UNKNOWN
    documents: dict[str, str] = field(default_factory=dict)
    physical_inspection: dict[str, str] = field(default_factory=dict)
    test_drive: dict[str, str] = field(default_factory=dict)
    obd_notes: str | None = None
    tyre_dot_codes: str | None = None
    seller_claims: str | None = None

    def to_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["repairs"] = [
            {
                **asdict(item),
                "observed_at": item.observed_at.isoformat(),
            }
            for item in self.repairs
        ]
        record["services"] = [
            {
                **asdict(item),
                "observed_at": item.observed_at.isoformat(),
            }
            for item in self.services
        ]
        return record

    @classmethod
    def empty(cls, car_id: str) -> "ConditionRecord":
        return cls(
            car_id=car_id,
            documents={key: UNKNOWN for key in DOCUMENT_FIELDS},
            physical_inspection={key: UNKNOWN for key in PHYSICAL_FIELDS},
            test_drive={key: UNKNOWN for key in TEST_DRIVE_FIELDS},
        )

    @classmethod
    def from_record(cls, record: dict[str, Any]) -> "ConditionRecord":
        return cls(
            car_id=record["car_id"],
            repairs=[
                Repair(
                    observed_at=date.fromisoformat(item["observed_at"]),
                    odometer_km=item.get("odometer_km"),
                    category=item["category"],
                    description=item["description"],
                    cost_inr=item.get("cost_inr"),
                    garage_type=item["garage_type"],
                )
                for item in record.get("repairs", [])
            ],
            services=[
                Service(
                    observed_at=date.fromisoformat(item["observed_at"]),
                    odometer_km=item.get("odometer_km"),
                    description=item["description"],
                    gap_notes=item.get("gap_notes"),
                )
                for item in record.get("services", [])
            ],
            accident_status=record.get("accident_status", UNKNOWN),
            repainted_panels=record.get("repainted_panels", UNKNOWN),
            airbag_deployed=record.get("airbag_deployed", UNKNOWN),
            documents={
                key: record.get("documents", {}).get(key, UNKNOWN)
                for key in DOCUMENT_FIELDS
            },
            physical_inspection={
                key: record.get("physical_inspection", {}).get(key, UNKNOWN)
                for key in PHYSICAL_FIELDS
            },
            test_drive={
                key: record.get("test_drive", {}).get(key, UNKNOWN)
                for key in TEST_DRIVE_FIELDS
            },
            obd_notes=record.get("obd_notes"),
            tyre_dot_codes=record.get("tyre_dot_codes"),
            seller_claims=record.get("seller_claims"),
        )
