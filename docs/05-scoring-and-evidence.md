# VeriCar — V1 Scoring & Evidence Model

## 1. Purpose

The scoring system exists to make evidence accumulation:

* transparent
* deterministic
* explainable
* testable
* reproducible

The LLM must never invent the final confidence score.

## 2. Three-Layer Evidence Model

```text
REPORT
  ↓
EVIDENCE
  ↓
FINDING
```

### Report

What a source submitted.

### Evidence

A report contributing to a finding.

### Finding

A synthesized conclusion supported by multiple pieces of evidence.

## 3. Source Types

Initial source-type priors:

| Source    | Prior |
| --------- | ----: |
| Owner     |  0.35 |
| Buyer     |  0.55 |
| Mechanic  |  0.75 |
| Inspector |  0.85 |

These are modeling priors.

They are not objective claims about the reliability of these professions.

## 4. Source Reliability

Source reliability means:

> How consistently has this source's historical reporting been corroborated or contradicted?

It does not measure:

* personality
* honesty as a character trait
* professional qualification
* legal credibility
* objective truthfulness

## 5. Historical Reliability

Use a Beta-Binomial style estimate:

```text
historical_reliability =
(alpha + corroborated)
/
(alpha + beta + resolved_reports)
```

V1 prior:

```text
alpha = 4
beta  = 1
```

Example:

```text
corroborated = 8
contradicted = 1
resolved = 9

historical_reliability =
(4 + 8) / (4 + 1 + 9)

= 12 / 14
≈ 85.7%
```

## 6. Prior + Historical Blend

A source with only one historical report should not radically change its reliability estimate.

Use:

```text
lambda =
resolved_reports / (resolved_reports + 5)
```

Then:

```text
effective_reliability =
(1 - lambda) × source_prior
+
lambda × historical_reliability
```

This causes historical evidence to have greater influence as sample size increases.

## 7. Corroboration

A report is corroborated when a later or independent observation supports the same underlying finding sufficiently strongly.

Example:

```text
Inspector:
"Hard 2→3 shift."

Later mechanic:
"Transmission hesitation during shifting."
```

These may corroborate each other.

## 8. Contradiction

A report is contradicted when sufficiently credible evidence conflicts with its relevant claim.

Example:

```text
Owner:
"No transmission problems."

Inspector:
"Hard 2→3 shift observed."
```

The original owner claim remains in the historical record.

## 9. Unresolved

If there is not enough later evidence to establish either corroboration or contradiction:

```text
unresolved
```

Example:

```text
Owner:
"Engine makes a strange noise."

No subsequent evidence.
```

This remains unresolved.

## 10. Independence

Independent source count matters.

Five people repeating the same copied information should not count as five independent observations.

V1 uses:

```text
unique source_id
+
no known copied/dependent report
=
potentially independent source
```

The system should preserve source identity.

## 11. Same-Source Repetition

Repeated observations from one source remain useful but do not increase independent-source count.

Example:

```text
Mechanic:
January — transmission hesitation

Mechanic:
February — transmission hesitation again
```

UI:

```text
1 independent source
Observed repeatedly across 31 days
```

not:

```text
2 independent sources
```

## 12. Evidence Weight

For each independent source contributing to a finding, use its effective source reliability.

Example:

```text
Inspector = 0.85
Mechanic  = 0.75
Buyer     = 0.55
```

If all support the same finding:

```text
support_weight = 0.85 + 0.75 + 0.55
               = 2.15
```

Contradicting sources contribute to:

```text
contradiction_weight
```

## 13. Evidence Direction

Calculate:

```text
direction =
support_weight /
(support_weight + contradiction_weight)
```

This represents the weighted balance of supporting versus contradicting evidence.

## 14. Evidence Sufficiency

Use:

```text
sufficiency =
1 - e^(-total_evidence_weight / 1.5)
```

where:

```text
total_evidence_weight =
support_weight + contradiction_weight
```

This prevents a single source from automatically producing near-perfect confidence.

## 15. Evidence Confidence

V1:

```text
evidence_confidence =
100 × direction × sufficiency
```

This is an **evidence-strength index**.

It is NOT:

* probability of mechanical failure
* probability that a defect objectively exists
* guaranteed diagnosis

Use the term:

> Evidence confidence

not:

> Probability of defect

## 16. Numerical Score Visibility

The numerical score should not dominate the UI.

Default:

```text
TRANSMISSION

Elevated concern

3 independent reports
Observed across 99 days

[ Evidence confidence ]
```

Clicking the button reveals the number and explanation.

## 17. Insufficient Evidence

Do not force a percentage when evidence is weak.

Possible qualitative states:

```text
Insufficient evidence
Limited evidence
Moderate evidence
Strong evidence
```

Exact numerical boundaries for these states should be finalized after testing the scoring model against the demo dataset.

## 18. Contradictions

Contradictions must remain visible.

Example:

```text
Owner:
"Transmission works perfectly."

Inspector:
"Hard 2→3 shift observed."

Mechanic:
"Transmission hesitation confirmed."
```

The system should communicate:

```text
Earlier owner reports described normal operation.

Two later independent professional reports
described transmission-related issues.
```

## 19. Majority Does Not Equal Truth

Do not implement:

```text
More people said X
→ X is true
```

Evidence should consider:

```text
source reliability
+
independence
+
corroboration
+
contradiction
+
historical behavior
```

## 20. Temporal Evidence

Record dates and observation span.

Example:

```text
January 10
February 18
March 4
April 19
May 2
```

The system can report:

```text
Observed across 112 days
```

Time span is useful explanatory context.

V1 should not arbitrarily multiply confidence merely because an issue is old or recent.

## 21. Semantic Issue Grouping

The LLM may identify semantically related descriptions:

```text
"hard 2→3 shift"

"gearbox hesitates between second and third"

"rough shift into third"
```

as a candidate common issue:

```text
transmission_shift_behavior
```

But the deterministic layer must validate the result before using it for scoring.

## 22. Evidence Ledger

For each finding, the system should be able to produce:

```json
{
  "finding": "transmission_shift_behavior",

  "supporting_sources": 3,
  "independent_sources": 3,
  "contradicting_sources": 1,

  "observation_span_days": 112,

  "support_weight": 2.15,
  "contradiction_weight": 0.35
}
```

The exact implementation can contain additional fields.

## 23. Example Scenarios

### No reports

```text
Insufficient evidence
```

### One owner report

```text
Limited evidence
```

### One inspector

```text
Elevated concern
Limited independent corroboration
```

### Inspector + mechanic

```text
Stronger evidence
2 independent professional sources
```

### Inspector + mechanic + buyer

```text
Strong accumulated evidence
3 independent sources
```

### Supporting + contradictory evidence

```text
Mixed evidence
```

The contradiction must be visible.

## 24. Important Constraint

Do not hardcode attractive demo values such as:

```text
86%
91%
```

The actual displayed values must come from the scoring engine and actual demo data.

## 25. Scoring Pipeline

```text
Report
  ↓
Validate
  ↓
Identify source
  ↓
Retrieve source history
  ↓
Calculate effective source reliability
  ↓
Identify candidate issue
  ↓
Retrieve related vehicle evidence
  ↓
Determine independent sources
  ↓
Separate supporting / contradicting evidence
  ↓
Calculate support weight
  ↓
Calculate contradiction weight
  ↓
Calculate direction
  ↓
Calculate sufficiency
  ↓
Calculate evidence confidence
  ↓
Assign qualitative assessment
  ↓
LLM explains result
```

## 26. Core Rule

The LLM explains the evidence.

The deterministic application calculates the evidence score.

Never reverse these responsibilities.
