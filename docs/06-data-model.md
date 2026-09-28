# VeriCar — V1 Data Model

## 1. Purpose

The data model provides the foundation for:

* Hindsight memory
* evidence calculation
* source reliability
* confidence calculation
* explainability
* API responses

The most important principle is:

> **Store raw facts and historical reports separately from derived assessments.**

Never store only a final score.

The system must retain enough underlying information to explain how the score was produced.

## 2. Core Entities

V1 contains six primary entities:

```text
Vehicle
Source
Report
Claim
Evidence
Finding
```

Relationship:

```text
VEHICLE
   │
   ├── REPORT ────────── SOURCE
   │       │
   │       └── CLAIM
   │
   └── FINDING
          │
          └── EVIDENCE
```

## 3. Vehicle

A vehicle is the primary memory subject.

Example:

```json
{
  "vehicle_id": "VEH-001",
  "vin": "VIN-VERICAR-001",
  "make": "Demo Motors",
  "model": "Apex",
  "year": 2022,
  "created_at": "2026-09-28T10:00:00Z"
}
```

Fields:

```text
vehicle_id
vin
make?
model?
year?
created_at
```

`vehicle_id` is the stable internal identifier.

VIN is the primary user-facing lookup identifier.

## 4. Source

A source is a person/entity submitting a report.

Example:

```json
{
  "source_id": "SRC-027",
  "source_type": "mechanic",
  "display_name": "Independent Mechanic #27",
  "created_at": "2026-09-28T10:05:00Z"
}
```

Allowed V1 source types:

```text
owner
buyer
mechanic
inspector
```

Do not collect unnecessary PII.

V1 does not require:

* phone
* address
* government ID
* unnecessary personal information

## 5. Report

A report represents what a source submitted.

Example:

```json
{
  "report_id": "RPT-004",
  "vehicle_id": "VEH-001",
  "source_id": "SRC-027",
  "source_type": "mechanic",
  "submitted_at": "2026-04-19T10:00:00Z",
  "text": "Transmission hesitation confirmed during test drive.",
  "status": "active"
}
```

Fields:

```text
report_id
vehicle_id
source_id
source_type
submitted_at
original_text
status
```

The original report text must be preserved.

## 6. Claim

A report may contain multiple claims.

Example report:

```text
"The transmission hesitates when shifting
and the brakes squeak."
```

This can become:

```text
REPORT
 ├── CLAIM
 │     └── transmission_shift_behavior
 │
 └── CLAIM
       └── brake_noise
```

Example:

```json
{
  "claim_id": "CLM-004",
  "report_id": "RPT-004",
  "text": "Transmission hesitation was observed.",
  "issue_candidate": "transmission_shift_behavior",
  "polarity": "supporting"
}
```

Possible polarity:

```text
supporting
contradicting
neutral
```

## 7. Finding

A finding is a synthesized conclusion about a vehicle.

Example:

```json
{
  "finding_id": "FND-001",
  "vehicle_id": "VEH-001",
  "issue": "transmission_shift_behavior",
  "title": "Transmission shift behavior",
  "status": "strong_evidence",
  "supporting_report_ids": [
    "RPT-003",
    "RPT-004",
    "RPT-005"
  ],
  "contradicting_report_ids": [
    "RPT-001",
    "RPT-002"
  ],
  "independent_supporting_sources": 3,
  "independent_contradicting_sources": 2,
  "observation_span_days": 99,
  "evidence_confidence": 82.4,
  "updated_at": "2026-09-28T10:30:00Z"
}
```

`evidence_confidence` is derived.

The underlying reports remain the source of truth.

## 8. Evidence

Evidence represents the relationship between a report and a finding.

Example:

```json
{
  "evidence_id": "EVD-008",
  "finding_id": "FND-001",
  "report_id": "RPT-004",
  "source_id": "SRC-027",
  "relationship": "supporting",
  "independent": true,
  "effective_source_reliability": 0.75,
  "reason": "Mechanic independently observed transmission hesitation."
}
```

Possible relationship:

```text
supporting
contradicting
```

Evidence should allow the system to trace:

```text
confidence
   ↓
evidence
   ↓
reports
   ↓
sources
```

## 9. Source Reliability

Source reliability is derived from source history.

Example:

```json
{
  "source_id": "SRC-027",
  "source_type": "mechanic",
  "source_prior": 0.75,
  "resolved_reports": 18,
  "corroborated_reports": 14,
  "contradicted_reports": 2,
  "unresolved_reports": 2,
  "historical_reliability": 0.857,
  "effective_reliability": 0.835,
  "updated_at": "2026-09-28T10:30:00Z"
}
```

This should be considered derived state.

The historical reports remain authoritative.

## 10. Independence

Evidence must retain source identity.

Example:

```json
{
  "evidence_id": "EVD-008",
  "report_id": "RPT-004",
  "finding_id": "FND-001",
  "independent": true
}
```

V1 independence is based on:

```text
unique source_id
+
no known copied/dependent report
```

A sophisticated dependency graph is not required for V1.

## 11. Contradictory Evidence

Example:

```json
{
  "evidence_id": "EVD-009",
  "finding_id": "FND-001",
  "report_id": "RPT-001",
  "source_id": "SRC-001",
  "relationship": "contradicting",
  "independent": true,
  "effective_source_reliability": 0.35
}
```

Contradictory reports are preserved.

They must not be deleted or silently averaged away.

## 12. Vehicle Assessment

A vehicle may contain multiple findings.

Example:

```text
Vehicle
│
├── Transmission → Strong evidence
├── Brake noise  → Limited evidence
└── Engine       → Insufficient evidence
```

Therefore V1 should not have one generic:

```text
vehicle_score
```

Instead, assessment is composed of issue-specific findings.

## 13. Raw vs Derived Data

### Raw / authoritative

```text
Vehicle
Source
Report
Claim
```

### Derived

```text
Evidence
Finding
Source reliability
Evidence confidence
Assessment status
```

This allows scoring logic to be changed without losing the original information.

## 14. Simplified Schema

```text
Vehicle
├── vehicle_id
├── vin
├── make?
├── model?
├── year?
└── created_at

Source
├── source_id
├── source_type
├── display_name?
└── created_at

Report
├── report_id
├── vehicle_id
├── source_id
├── submitted_at
├── original_text
└── status

Claim
├── claim_id
├── report_id
├── text
├── issue_candidate
└── polarity

Evidence
├── evidence_id
├── finding_id
├── report_id
├── source_id
├── relationship
├── independent
└── effective_source_reliability

Finding
├── finding_id
├── vehicle_id
├── issue
├── status
├── evidence_confidence
└── updated_at
```

## 15. Example Complete Flow

```text
VEH-001
   │
   ├── RPT-001
   │     └── Owner
   │           └── "Vehicle runs perfectly."
   │
   ├── RPT-002
   │     └── Inspector
   │           └── "Hard 2→3 shift observed."
   │
   └── RPT-003
         └── Mechanic
               └── "Transmission hesitation confirmed."
```

The evidence layer then produces:

```text
FND-001
Transmission shift behavior

Supporting:
RPT-002
RPT-003

Contradicting:
RPT-001
```

The scoring engine uses these relationships to calculate evidence confidence.

## 16. Design Principle

Do not create:

```text
vehicle.ai_score
vehicle.trust_score
```

These names are ambiguous.

Prefer:

```text
finding.evidence_confidence
source.effective_reliability
```

The names should communicate exactly what the value represents.

## 17. Next Layer

After this data model, the next architecture task is:

```text
DATA MODEL
     ↓
HINDSIGHT MEMORY DESIGN
```

We need to determine exactly:

* what is written to Hindsight
* when it is written
* how vehicle memories are organized
* how source memories are organized
* what is retrieved during a new report
* how retrieved memory feeds the evidence engine
* what remains in application state versus Hindsight

Only after this should implementation begin.
