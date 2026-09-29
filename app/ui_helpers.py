from __future__ import annotations

from typing import Any


_HISTORY_COPY: dict[str, dict[str, str]] = {
    "MATCHED": {
        "eyebrow": "HISTORY CHECK",
        "title": "VeriCar has seen this car before",
        "body": "Today's information matches the previous record in the areas we could compare.",
        "tone": "matched",
        "action": "",
    },
    "CHANGED": {
        "eyebrow": "HISTORY CHECK",
        "title": "Some things have changed since the last record",
        "body": "VeriCar found updates worth reviewing before you make a decision.",
        "tone": "changed",
        "action": "",
    },
    "CONTRADICTION": {
        "eyebrow": "VERIFY BEFORE BUYING",
        "title": "Something doesn't match the previous record",
        "body": "This is a discrepancy between records, not proof of dishonesty. Verify the detail with original documents or an independent inspection.",
        "tone": "contradiction",
        "action": "Verify this before buying",
    },
    "INSUFFICIENT": {
        "eyebrow": "HISTORY CHECK",
        "title": "There is an earlier record, but not enough to compare confidently",
        "body": "Some information is missing or unknown, so this check cannot make a reliable comparison.",
        "tone": "insufficient",
        "action": "",
    },
    "NO_HISTORY": {
        "eyebrow": "HISTORY CHECK",
        "title": "No previous VeriCar record found for this vehicle.",
        "body": "This does not mean the car has no history. It means VeriCar does not currently have a matching record.",
        "tone": "no-history",
        "action": "",
    },
    "UNAVAILABLE": {
        "eyebrow": "HISTORY CHECK",
        "title": "Vehicle history is temporarily unavailable.",
        "body": "VeriCar could not reach its history service. This is different from finding no history, so the current assessment should be reviewed with that limitation in mind.",
        "tone": "unavailable",
        "action": "",
    },
}

_VERDICT_COPY: dict[str, dict[str, str]] = {
    "BUY": {
        "label": "BUY",
        "title": "Looks reasonable based on the information provided",
        "tone": "buy",
    },
    "NEGOTIATE": {
        "label": "NEGOTIATE",
        "title": "Consider negotiating before buying",
        "tone": "negotiate",
    },
    "AVOID": {
        "label": "AVOID",
        "title": "Important issues need to be resolved before buying",
        "tone": "avoid",
    },
}

_FIELD_LABELS = {
    "accident_status": "Accident history",
    "airbag_deployed": "Airbag deployment",
    "repainted_panels": "Repainted panels",
    "odometer_km": "Odometer reading",
    "repairs": "Repair history",
    "services": "Service history",
    "documents.rc_match": "RC and vehicle details",
    "documents.insurance_valid": "Insurance validity",
    "documents.insurance_claim_history": "Insurance claim history",
    "documents.no_claim_bonus": "No-claim bonus",
    "documents.puc_valid": "PUC validity",
    "documents.loan_hypothecation_closed": "Loan closure",
    "documents.form_29_30_available": "Form 29/30",
    "documents.vin_matches_rc": "VIN and RC match",
    "physical_inspection.ac_works": "AC inspection",
    "physical_inspection.panel_gaps_or_paint_mismatch": "Panel and paint condition",
    "physical_inspection.rust": "Rust inspection",
    "physical_inspection.oil_or_coolant_leaks": "Oil or coolant leaks",
    "test_drive.hesitation": "Test-drive hesitation",
    "test_drive.engine_noise": "Engine noise",
    "test_drive.brakes_pull_or_spongy": "Brake feel",
    "test_drive.steering_play": "Steering feel",
}


def history_status_copy(status: str) -> dict[str, str]:
    """Return safe, buyer-facing copy for a reconciliation status."""
    return dict(_HISTORY_COPY.get(status, _HISTORY_COPY["INSUFFICIENT"]))


def verdict_copy(verdict: str) -> dict[str, str]:
    """Return plain-language copy while preserving the deterministic label."""
    return dict(_VERDICT_COPY.get(verdict, _VERDICT_COPY["NEGOTIATE"]))


def _display_value(value: Any) -> str:
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,} km" if value >= 1000 else str(value)
    return str(value)


def humanize_history_finding(finding: Any) -> str:
    """Translate an internal finding into concise buyer language."""
    label = _FIELD_LABELS.get(finding.field, finding.field.replace("_", " ").replace(".", " — ").capitalize())
    current = _display_value(finding.current_value)
    historical = _display_value(finding.historical_value)
    if finding.kind == "MATCH":
        return f"{label} matches the previous record: {current}."
    if finding.kind == "CONTRADICTION":
        return f"Previous record: {label} — {historical}. Today's entry: {label} — {current}."
    if finding.kind == "CHANGED":
        return f"{label} changed from {historical} to {current}."
    return getattr(finding, "message", f"{label} needs more information.")
