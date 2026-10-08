from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.models.memory import VehicleReport


SourceType = Literal["owner", "buyer", "mechanic", "inspector"]
ClaimPolarity = Literal["supporting", "contradicting", "unresolved"]

REPORT_TEXT_MAX_LENGTH = 10_000


class ReportSubmission(BaseModel):
    """Validated API payload for a vehicle history report."""

    model_config = ConfigDict(extra="forbid")

    vehicle_id: str = Field(min_length=1, max_length=100)
    vin: str | None = Field(default=None, min_length=1, max_length=100)
    source_id: str = Field(min_length=1, max_length=100)
    source_type: SourceType
    observed_at: date
    text: str = Field(min_length=1, max_length=REPORT_TEXT_MAX_LENGTH)

    @field_validator("vehicle_id", "source_id", "text", "vin")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class VehicleCreateRequest(BaseModel):
    """Validated API payload for creating or updating a vehicle record."""

    model_config = ConfigDict(extra="forbid")

    car_id: str | None = Field(default=None, min_length=1, max_length=100)
    brand: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    manufacture_year: int | None = Field(default=None, ge=1980, le=2050)
    manufacture_month: int | None = Field(default=None, ge=1, le=12)
    registration_date: date | None = None
    purchase_date: date | None = None
    variant: str | None = Field(default=None, max_length=100)
    fuel_type: str | None = Field(default=None, max_length=50)
    transmission: str | None = Field(default=None, max_length=50)
    odometer_km: int | None = Field(default=None, ge=0)
    asking_price_inr: int | None = Field(default=None, ge=0)
    previous_owners: int | None = Field(default=None, ge=0)
    vin: str | None = Field(default=None, max_length=100)
    registration_state: str | None = Field(default=None, max_length=10)

    @field_validator("car_id", "brand", "model", "variant", "fuel_type", "transmission", "vin", "registration_state")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value


class Claim(BaseModel):
    """A structured interpretation of what a report states."""

    claim_id: str
    report_id: str
    text: str
    issue_candidate: str | None
    polarity: ClaimPolarity


def generate_report_id(
    idempotency_key: str | None = None,
    request_fingerprint: str | None = None,
) -> str:
    if idempotency_key is None:
        return f"RPT-{uuid4().hex.upper()}"

    identity = f"{idempotency_key.strip()}\0{request_fingerprint or ''}"
    return f"RPT-{uuid5(NAMESPACE_URL, identity).hex.upper()}"


def generate_claim_id() -> str:
    return f"CLM-{uuid4().hex[:12].upper()}"


def to_vehicle_report(
    report_id: str,
    request: ReportSubmission,
    submitted_at: datetime,
    claim: Claim | None = None,
) -> VehicleReport:
    """Convert an API submission into the application's memory model."""
    observed_at = datetime.combine(
        request.observed_at,
        time.min,
        tzinfo=timezone.utc,
    )

    return VehicleReport(
        report_id=report_id,
        vin=request.vin,
        source_id=request.source_id,
        source_type=request.source_type,
        text=request.text,
        observed_at=observed_at,
        vehicle_id=request.vehicle_id,
        submitted_at=submitted_at,
        issue_candidate=claim.issue_candidate if claim else None,
        polarity=claim.polarity if claim else "unresolved",
    )


def build_claim(report_id: str, text: str) -> Claim:
    """Create a deterministic V1 claim without making a mechanical diagnosis."""
    normalized = " ".join(text.split())
    lower = normalized.lower()

    if any(
        phrase in lower
        for phrase in (
            "no issue",
            "no problem",
            "works perfectly",
            "working perfectly",
            "excellent condition",
        )
    ):
        polarity: ClaimPolarity = "contradicting"
    elif any(
        phrase in lower
        for phrase in (
            "issue",
            "problem",
            "hesitation",
            "hard shift",
            "rough shift",
            "failure",
            "delayed shift",
        )
    ):
        polarity = "supporting"
    else:
        polarity = "unresolved"

    if any(
        term in lower
        for term in ("transmission", "gearbox", "shift", "shifting", "gear")
    ):
        issue_candidate = "transmission_shift_behavior"
    else:
        issue_candidate = None

    claim_text = (
        normalized
        if issue_candidate is None
        else f"{normalized}"
    )

    return Claim(
        claim_id=generate_claim_id(),
        report_id=report_id,
        text=claim_text,
        issue_candidate=issue_candidate,
        polarity=polarity,
    )
