# VeriCar — Product Requirements

## 1. Product Purpose

VeriCar helps used-car buyers understand accumulated vehicle evidence and identify issues that may warrant further inspection.

The product is designed around a simple principle:

> A vehicle assessment should improve as relevant, trustworthy evidence accumulates over time.

VeriCar is not intended to guarantee vehicle quality, detect every hidden defect, or replace a professional inspection.

## 2. Persistent Evidence Is a Core Capability

Historical evidence is central to the product rather than an invisible storage concern.

The intended progression is:

```text
Historical reports
      ↓
Relevant evidence
      ↓
Corroboration and source context
      ↓
Deterministic assessment
      ↓
Explainable recommendation
```

A new report should be interpreted in the context of relevant previous observations.

## 3. Reference Assessment Workflow

The canonical workflow is:

```text
Identify vehicle
      ↓
Retrieve durable history
      ↓
Retrieve relevant memory
      ↓
View current assessment
      ↓
Submit a new report
      ↓
Persist the report
      ↓
Process external memory
      ↓
Recalculate evidence
      ↓
Update assessment
      ↓
Explain material changes
```

The browser application should make this progression understandable without requiring the user to understand the underlying infrastructure.

## 4. Reference Evidence Scenario

The following synthetic scenario illustrates the intended behavior. It is a development and demonstration fixture, not real-world vehicle data.

Example vehicle:

```text
VIN-VERICAR-001
```

### Stage 0 — Insufficient Evidence

```text
No relevant history found.

There is not enough evidence to assess this vehicle.

Recommendation:
Obtain an independent inspection.
```

### Stage 1 — Owner Reports

Two owner reports:

```text
"Vehicle runs perfectly."

"No known issues."
```

The system should recognize that these are owner observations and that independent corroboration is still limited.

### Stage 2 — Independent Inspection

Inspector report:

```text
"Hard 2→3 shift observed during inspection."
```

The assessment should increase concern for the transmission because an independent inspection introduced a specific observation.

### Stage 3 — Mechanic Confirmation

Mechanic report:

```text
"Transmission hesitation confirmed."
```

The assessment should reflect stronger evidence because another professional source corroborates the earlier observation.

### Stage 4 — Additional Buyer Observation

Previous buyer report:

```text
"Experienced hard shifting during test drive."
```

The system now has multiple observations from distinct sources over time.

## 5. Explainable Assessment Changes

A user should be able to understand why the assessment changed.

For the reference scenario, the explanation should distinguish:

```text
Earlier history:
Owner reports described normal operation.

Later evidence:
An independent inspection reported hard 2→3 shifting.

Corroboration:
A mechanic reported similar transmission hesitation.

Additional context:
A previous buyer described hard shifting during a test drive.

Result:
Independent observations accumulated and increased the
strength of the transmission-related evidence.
```

The explanation must remain grounded in the evidence available to the assessment pipeline.

## 6. Evidence and Source Semantics

The product must preserve distinctions between:

- owner observations
- independent inspections
- mechanic reports
- previous-buyer observations
- unknown or missing information

Repeated observations from one source must not be treated as equivalent to independent corroboration from multiple sources.

Unknown information must remain unknown. It must not silently become negative evidence.

## 7. Failure and Availability Semantics

The product must distinguish successful empty results from unavailable dependencies.

For example:

```text
Successful memory lookup
→ no relevant history found

Memory service unavailable
→ memory unavailable
```

The second state must never be rendered as though the vehicle has no history.

Durable local history should remain available when external memory or explanation services fail.

## 8. Real-World Scope

VeriCar is intended to help users:

- organize fragmented vehicle information
- understand accumulated evidence
- identify recurring or corroborated issues
- understand why an assessment changed
- identify issues that may warrant further inspection

VeriCar does not claim to:

- guarantee vehicle quality
- detect every hidden defect
- prevent bad purchases
- replace a qualified inspection or mechanic

The product should communicate these boundaries clearly in user-facing experiences.

## 9. Synthetic Data Policy

Synthetic vehicles, reports, profiles, and source histories may be used for development, testing, and demonstrations.

Synthetic data must remain explicitly labeled and must never be presented as authoritative manufacturer information or real-world vehicle history.

## 10. Product Design Principle

The product should prioritize one coherent, understandable workflow over a large collection of loosely connected features.

The primary experience is:

```text
History
  ↓
Evidence
  ↓
Assessment
  ↓
Explanation
  ↓
New evidence
  ↓
Updated assessment
```

Each stage should be traceable to the evidence and system state that produced it.
