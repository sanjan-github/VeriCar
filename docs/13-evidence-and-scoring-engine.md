# VeriCar — Evidence & Scoring Engine Specification

## 1. Purpose

The Evidence & Scoring Engine converts accumulated vehicle reports and source history into a deterministic assessment of the available evidence.

It answers:

> "Given everything VeriCar has historically observed about this vehicle, how strongly does the available evidence support a particular finding?"

The engine must distinguish between:

* what a source reported
* how historically reliable that source has been
* whether different reports are independent
* whether reports support or contradict one another
* how much accumulated evidence exists
* how the assessment changes as new reports arrive

The engine must not claim that a vehicle definitely has a mechanical defect.

Its output is an:

> **evidence-strength estimate**

not a probability, diagnosis, or guarantee.

---

# 2. Scope

This stage consumes:

* structured reports
* claims
* Hindsight vehicle history
* Hindsight source history
* source types
* historical corroboration
* historical contradiction
* observation dates

It produces:

* source reliability
* evidence relationships
* supporting evidence
* contradicting evidence
* evidence confidence
* qualitative evidence status
* assessment-change explanation data

It does NOT handle:

* report ingestion
* Hindsight API implementation
* LLM-generated explanations
* frontend rendering
* mechanical diagnosis
* purchase recommendations

---

# 3. Architectural Position

The reasoning pipeline is:

```
Report
   |
   v
Claim
   |
   v
Hindsight Retrieval
   |
   v
Evidence Engine
   |
   +-------------------------+
   |                         |
   v                         v
Deterministic           Evidence State
calculations                 |
   |                         |
   +------------+------------+
                |
                v
          Groq Explanation
                |
                v
             UI
```

Python/application logic owns the calculations.

Hindsight provides historical memory.

Groq explains the resulting evidence state.

---

# 4. Core Principle

The system must not use:

```
number of reports = truth
```

Instead:

```
evidence strength
    =
source reliability
+ independence
+ corroboration
+ contradiction
+ accumulated evidence
+ historical context
```

A larger number of reports does not automatically mean stronger evidence.

For example:

```
5 reports from the same owner
```

is not equivalent to:

```
3 independent reports from an inspector,
mechanic, and previous buyer.
```

---

# 5. Source Reliability vs Evidence Confidence

These are separate concepts.

## Source Reliability

Source reliability answers:

> "How reliable has this source's reporting historically been?"

It is associated with the source.

Example:

```
SRC-027
mechanic
historical reliability = 0.84
```

## Evidence Confidence

Evidence confidence answers:

> "How strongly does the accumulated evidence support this particular finding?"

It is associated with a finding.

Example:

```
transmission_shift_behavior
evidence confidence = 82
```

A reliable source does not automatically mean that every claim from that source is true.

Similarly, a finding can have strong evidence even though no individual source has perfect reliability.

---

# 6. Initial Source Priors

V1 uses initial source priors:

```
owner       = 0.35
buyer       = 0.55
mechanic    = 0.75
inspector   = 0.85
```

These values are modeling priors for the prototype.

They are NOT:

* professional qualification ratings
* objective measurements of expertise
* probabilities that a source is truthful
* claims about real-world source populations

They provide a starting point before sufficient historical reporting behavior exists.

---

# 7. Historical Reliability

Historical reliability is calculated from resolved historical reports.

For a source:

```
historical_reliability =
    (alpha + corroborated) /
    (alpha + beta + resolved_reports)
```

Use:

```
alpha = 4
beta  = 1
```

Where:

```
corroborated
    = number of historically corroborated reports

resolved_reports
    = corroborated + contradicted
```

Unresolved reports are not treated as either success or failure.

---

# 8. Why Smoothing Is Required

A source with only one resolved report should not experience a dramatic reliability change.

Example:

```
source prior = 0.35
```

If the source's first report is corroborated, the system should not immediately treat the source as extremely reliable.

The alpha/beta parameters provide smoothing.

This prevents tiny samples from producing extreme values.

---

# 9. Effective Source Reliability

The system combines the initial source prior with historical behavior.

Define:

```
lambda =
    resolved_reports /
    (resolved_reports + 5)
```

Then:

```
effective_reliability =
    (1 - lambda) * source_prior
    +
    lambda * historical_reliability
```

Interpretation:

* very little history → prior has more influence
* increasing history → observed behavior has more influence
* sufficient history → historical behavior increasingly dominates

This prevents early reports from causing large reliability swings.

---

# 10. Example

Suppose an owner begins with:

```
source_prior = 0.35
```

After several resolved reports:

```
corroborated = 6
contradicted = 1
```

Then:

```
resolved_reports = 7
```

Historical reliability:

```
(4 + 6) / (4 + 1 + 7)

= 10 / 12

= 0.8333
```

Then:

```
lambda = 7 / (7 + 5)
       = 0.5833
```

The effective reliability blends:

```
35% prior
```

with:

```
83.33% historical reliability
```

according to lambda.

The application should calculate this programmatically rather than hard-coding the resulting value.

---

# 11. Report Independence

Independence matters because multiple reports from the same source should not be treated as independent corroboration.

V1 independence rule:

Two reports are potentially independent when:

* they come from different source IDs
* there is no known evidence that one was copied from or directly dependent on the other

Example:

```
SRC-001
    Report A

SRC-002
    Report B
```

These may provide independent evidence.

But:

```
SRC-001
    Report A
    Report B
    Report C
```

does not represent three independent sources.

The reports should remain separate historically, but the evidence engine must avoid counting them as three independent corroborators.

---

# 12. Evidence Polarity

Each claim should contribute to a finding with a polarity.

Supported states:

```
supporting
contradicting
unresolved
```

Example:

```
Claim:
"Transmission hesitation observed."

Finding:
transmission_shift_behavior

polarity:
supporting
```

Another report:

```
"Transmission shifted smoothly during inspection."

polarity:
contradicting
```

The original claims remain preserved.

---

# 13. Evidence Classification

Evidence classification should be based on the relationship between a claim and the finding being evaluated.

The engine should determine whether a historical claim:

* supports the finding
* contradicts the finding
* cannot currently resolve the finding

The LLM may help identify semantic relationships, but the final evidence state must be validated and represented structurally.

---

# 14. Semantic Issue Matching

Different wording may refer to the same underlying issue.

Examples:

```
"Hard 2->3 shift"

"Rough shift into third"

"Transmission hesitation"
```

These may correspond to:

```
transmission_shift_behavior
```

The engine should operate on normalized issue candidates rather than exact text matching wherever possible.

The original text must remain available for traceability.

---

# 15. Supporting Evidence

For a finding:

```
support_weight
```

is the sum of the effective reliability of independent supporting sources.

Conceptually:

```
support_weight =
    sum(
        effective_reliability(source)
        for independent supporting sources
    )
```

Repeated reports from the same source should not be treated as additional independent source weight.

---

# 16. Contradicting Evidence

For the same finding:

```
contradiction_weight
```

is the sum of the effective reliability of independent contradicting sources.

Conceptually:

```
contradiction_weight =
    sum(
        effective_reliability(source)
        for independent contradicting sources
    )
```

Contradictory evidence must remain visible.

The engine must never silently discard it.

---

# 17. Direction of Evidence

If supporting and contradicting evidence both exist:

```
direction =
    support_weight /
    (support_weight + contradiction_weight)
```

Interpretation:

* closer to 1 → evidence leans toward the finding
* closer to 0 → evidence leans against the finding
* around 0.5 → evidence is substantially conflicted

This is a directional evidence measure.

It is NOT a probability that the finding is true.

---

# 18. Evidence Sufficiency

The direction alone is insufficient.

A single source with high reliability should not automatically produce strong confidence.

The system therefore calculates evidence sufficiency.

Use:

```
sufficiency =
    1 - exp(
        -total_evidence_weight / 1.5
    )
```

where:

```
total_evidence_weight =
    support_weight + contradiction_weight
```

This makes confidence increase as evidence accumulates while producing diminishing returns.

---

# 19. Evidence Confidence

The final evidence-strength index is:

```
evidence_confidence =
    100
    * direction
    * sufficiency
```

where:

```
direction =
    support_weight /
    (support_weight + contradiction_weight)
```

and:

```
sufficiency =
    1 - exp(
        -total_evidence_weight / 1.5
    )
```

The result is a 0–100 index.

It must NOT be described as:

```
probability of failure
probability of defect
probability the vehicle is unsafe
percentage chance that the claim is true
```

It represents the strength and direction of the currently available evidence.

---

# 20. Weak-Evidence Protection

A numerical value should not create a false impression of certainty.

When the total evidence is very small, the UI should prefer a qualitative state such as:

```
Insufficient evidence
```

rather than presenting a precise-looking percentage.

The exact thresholds must be validated against representative scenarios before they are frozen.

---

# 21. Qualitative Evidence States

V1 should support:

```
Insufficient evidence
Limited evidence
Moderate evidence
Strong evidence
```

These labels describe accumulated evidence strength.

They are not risk categories.

They are not mechanical diagnoses.

The thresholds must be tested using realistic demo scenarios before final implementation.

---

# 22. Threshold Validation

Before freezing thresholds, run the model against at least 6–8 representative scenarios.

Required scenarios include:

### Scenario A

One low-reliability owner report.

Expected behavior:

```
insufficient or limited evidence
```

### Scenario B

Two reports from the same owner.

Expected behavior:

```
more historical information
but not equivalent to two independent sources
```

### Scenario C

Owner report + inspector report supporting the same issue.

Expected behavior:

```
stronger evidence
```

### Scenario D

Inspector + mechanic independently supporting the same issue.

Expected behavior:

```
strong accumulated support
```

### Scenario E

High-quality supporting evidence + credible contradiction.

Expected behavior:

```
contradiction remains visible
confidence is moderated
```

### Scenario F

Many repeated reports from one source.

Expected behavior:

```
repetition does not create equivalent independent corroboration
```

### Scenario G

Multiple independent sources supporting the issue over time.

Expected behavior:

```
evidence strength increases
```

### Scenario H

Conflicting evidence with similar source reliability.

Expected behavior:

```
evidence remains conflicted
system does not manufacture certainty
```

Thresholds should be frozen only after observing these scenarios.

---

# 23. Temporal Evidence

Each report has an observation date.

The engine must preserve temporal ordering.

Example:

```
Day 0
Owner:
"Transmission operates normally."

Day 99
Inspector:
"Hard 2->3 shift."

Day 112
Mechanic:
"Transmission hesitation."
```

The later reports provide additional historical evidence.

The engine should use dates to explain how the evidence evolved.

V1 should NOT arbitrarily multiply confidence simply because an observation is newer or because reports span a particular number of days.

Time is primarily explanatory context in V1.

---

# 24. Contradiction Preservation

Contradictions are first-class evidence.

Example:

```
Owner:
"Transmission works perfectly."

Inspector:
"Hard 2->3 shift."

Mechanic:
"Transmission hesitation."
```

The system should preserve all three observations.

The resulting finding can say:

```
Earlier owner reporting described normal operation,
while later independent inspection and mechanic reports
described transmission-related concerns.
```

The system must not replace the original owner report with the later reports.

---

# 25. Same Finding, Different Time

Reports may describe different states of the vehicle at different times.

Example:

```
2026-01-01
Owner:
"No transmission problems noticed."

2026-05-01
Inspector:
"Hard shifting observed."
```

These are not necessarily logical contradictions.

They may represent a change in vehicle condition.

The system should retain both observations and allow the timeline to provide the context.

---

# 26. Source History Updates

When a report is later resolved as corroborated or contradicted, the source's historical record should be updated.

Example:

```
Source:
SRC-027

Reports:
12

Corroborated:
9

Contradicted:
2

Unresolved:
1
```

The evidence engine can then calculate the source's historical reliability.

The source's historical reliability should be derived from its reporting history rather than manually edited by the user.

---

# 27. Resolution State

A report may initially be:

```
unresolved
```

because there is not enough later evidence to evaluate it.

Later reports can establish:

```
corroborated
```

or:

```
contradicted
```

Resolution must be based on subsequent evidence.

The system should preserve the original report and record the resolution event rather than rewriting history.

---

# 28. Finding Model

Conceptually, a finding may contain:

{
"finding_id": "FND-001",
"vehicle_id": "VEH-001",
"issue": "transmission_shift_behavior",
"supporting_claims": [
"CLM-004",
"CLM-008"
],
"contradicting_claims": [
"CLM-002"
],
"independent_supporting_sources": [
"SRC-027",
"SRC-041"
],
"independent_contradicting_sources": [
"SRC-003"
],
"support_weight": 1.69,
"contradiction_weight": 0.35,
"evidence_confidence": 72,
"evidence_status": "moderate"
}

The exact values above are illustrative.

The implementation must calculate them rather than hard-code them.

---

# 29. Assessment Evolution

Every new report can change the evidence state.

Example:

## State 0

No historical reports.

```
Evidence status:
Insufficient evidence
```

## State 1

Owner report:

```
"Transmission feels normal."

Evidence:
Limited
```

## State 2

Inspector report:

```
"Hard 2->3 shift."

Evidence:
Moderate concern
```

## State 3

Mechanic report:

```
"Transmission hesitation confirmed."

Evidence:
Stronger accumulated evidence
```

## State 4

Previous buyer reports the same behavior.

```
Evidence:
Strong accumulated support
```

The important product behavior is not just the final number.

The system must be able to explain:

> Why did the assessment change?

---

# 30. Assessment Change Record

When the evidence state changes, the application should retain enough structured information to explain the change.

Example:

{
"previous_status": "limited",
"new_status": "moderate",
"trigger_report_id": "RPT-009",
"new_supporting_source": "SRC-041",
"reason": "Independent mechanic report supported the existing transmission finding."
}

The explanation text itself may later be generated by Groq.

The underlying facts must come from deterministic application state.

---

# 31. Evidence Calculation Order

For each finding:

```
1. Retrieve relevant vehicle history
2. Retrieve relevant source history
3. Identify related claims
4. Group claims by normalized issue
5. Determine support/contradiction
6. Identify independent sources
7. Calculate source effective reliability
8. Calculate support weight
9. Calculate contradiction weight
10. Calculate direction
11. Calculate sufficiency
12. Calculate evidence confidence
13. Determine qualitative status
14. Record assessment change
15. Return structured result
```

This order should remain deterministic.

---

# 32. Hindsight's Role

Hindsight is critical because the engine requires historical context.

Without historical memory, the system would only see the current report.

With Hindsight:

```
current report
      +
previous observations
      +
source history
      +
previous contradictions
      +
previous corroboration
```

become available for reasoning.

Hindsight supplies the historical evidence.

The application calculates the resulting evidence state.

---

# 33. Hindsight Retrieval Requirements

Retrieval should include:

* relevant reports
* historical observations
* source history
* corroboration information
* contradiction information
* temporal context

Retrieval should not return only the most recent positive reports.

Contradictory evidence must remain retrievable.

---

# 34. Empty vs Unavailable Memory

The engine must distinguish:

### Empty history

Hindsight successfully responds and there is no relevant historical evidence.

Meaning:

```
No known history.
```

### Memory unavailable

Hindsight failed or could not be reached.

Meaning:

```
Historical evidence could not be retrieved.
```

These states must never be treated as equivalent.

---

# 35. LLM Boundary

Groq may be used after the deterministic evidence state has been calculated.

Groq can:

* summarize evidence
* group semantically related observations
* explain assessment changes
* produce natural-language reasoning

Groq must not independently calculate:

* source reliability
* corroboration counts
* contradiction counts
* evidence confidence
* report dates
* report counts
* historical facts

The backend should provide these values to the LLM as structured facts.

---

# 36. Example Explanation Input

The backend might provide Groq:

{
"finding": "transmission_shift_behavior",
"evidence_status": "strong",
"evidence_confidence": 86,
"independent_supporting_sources": 3,
"supporting_reports": 4,
"contradicting_reports": 1,
"observation_span_days": 112,
"historical_context": [
"Owner previously reported normal operation.",
"Inspector later observed hard 2->3 shifting.",
"Mechanic later confirmed transmission hesitation."
]
}

Groq can turn this into readable explanation.

It cannot change:

```
86
```

into:

```
92
```

or invent another source.

---

# 37. Example Product Output

The application may eventually expose:

```
TRANSMISSION

Elevated concern

3 independent reports
Observed across 112 days

[ Why this assessment? ]

[ Evidence confidence ]
```

The expanded evidence panel may show:

```
EVIDENCE CONFIDENCE
86%

Based on:
• 3 independent sources
• repeated observations
• source reporting history
• supporting and contradicting evidence
• historical observation span

Evidence-based estimate.
Not a probability or mechanical diagnosis.
```

The UI implementation belongs to a later stage.

---

# 38. Source Reliability Display

If source reliability is exposed to the user, it should include context.

Example:

```
SOURCE RELIABILITY

Estimated reliability: 91%

Reports: 18
Corroborated: 14
Contradicted: 2
Unresolved: 2

This estimate is based on historical
reporting behavior.

It is not a measure of professional
qualification.
```

Do not imply that a numerical reliability value represents professional certification or expertise.

---

# 39. Safety Language

The system should describe its output as:

```
evidence-based estimate
```

and not:

```
diagnosis
guaranteed condition
probability of defect
professional inspection
```

Recommended explanatory language:

```
"VeriCar assessments are based on the reports available to the system. Reports may be incomplete, inaccurate, outdated, or contradictory. Confidence values describe the available evidence. They are not guarantees, professional qualifications, or mechanical diagnoses."
```

---

# 40. Edge Case — One High-Reliability Report

A single inspector report may have a high effective reliability.

However:

```
high source reliability
    !=
sufficient accumulated evidence
```

The system should avoid presenting one report as equivalent to independently corroborated history.

---

# 41. Edge Case — Many Low-Reliability Reports

Several low-reliability reports may collectively contribute evidence.

However, their combined weight should not automatically override stronger contradictory evidence.

The engine must evaluate:

```
source reliability
independence
support
contradiction
```

together.

---

# 42. Edge Case — Same Source Repeats

Example:

```
SRC-001
    Report 1
    Report 2
    Report 3
    Report 4
```

The source history may become more informative.

However, the system must not interpret this as:

```
4 independent sources
```

It remains:

```
1 source
4 observations
```

---

# 43. Edge Case — Contradictory Independent Sources

Example:

```
Inspector:
"Hard shifting."

Mechanic:
"Transmission operates normally."
```

Both claims should remain visible.

The result should reflect the competing evidence.

The engine must not hide the contradiction merely to produce a clean verdict.

---

# 44. Edge Case — No Evidence

If there are no relevant historical reports:

```
evidence_status =
    Insufficient evidence
```

The system should not invent a finding.

It should state that the available history is insufficient.

---

# 45. Edge Case — Hindsight Failure

If Hindsight is unavailable:

```
evidence calculation must not pretend
historical evidence was successfully retrieved.
```

The response should expose an explicit memory-unavailable state.

The application should not return:

```
"No history found."
```

---

# 46. Determinism

Given the same:

* reports
* source histories
* claims
* timestamps
* Hindsight retrieval results
* configuration

the evidence engine should produce the same result.

This is important for:

* debugging
* testing
* reproducibility
* trust
* hackathon demonstration

---

# 47. Configuration

Scoring constants should be centralized.

Example configuration:

```
SOURCE_PRIORS
ALPHA
BETA
RELIABILITY_HISTORY_SCALE
SUFFICIENCY_SCALE
EVIDENCE_STATUS_THRESHOLDS
```

Do not scatter numeric constants throughout the codebase.

Thresholds should be configurable until validation is complete.

---

# 48. Testing Strategy

The evidence engine should be tested independently of:

* FastAPI
* frontend
* Groq
* live Hindsight

Core calculations should accept structured inputs and return structured outputs.

This allows deterministic unit testing.

---

# 49. Required Unit Tests

At minimum:

[ ] source prior is selected correctly

[ ] historical reliability is calculated correctly

[ ] unresolved reports do not count as resolved

[ ] effective reliability is calculated correctly

[ ] same source is not counted as independent

[ ] independent sources are counted separately

[ ] supporting evidence contributes to support weight

[ ] contradicting evidence contributes to contradiction weight

[ ] direction is calculated correctly

[ ] sufficiency increases with accumulated evidence

[ ] evidence confidence stays within 0–100

[ ] contradictions remain represented

[ ] insufficient evidence is handled

[ ] assessment changes can be detected

[ ] identical inputs produce identical outputs

---

# 50. Integration Tests

After unit tests pass, test the complete flow:

```
Report
   ↓
Hindsight retrieval
   ↓
Evidence engine
   ↓
Assessment
```

Required integration scenarios:

1. Unknown vehicle
2. Single owner report
3. Multiple owner reports
4. Owner + inspector
5. Inspector + mechanic
6. Multiple independent sources
7. Supporting + contradicting evidence
8. Repeated same-source reports
9. Hindsight empty
10. Hindsight unavailable

---

# 51. Definition of Done

The Evidence & Scoring Engine is complete when:

[ ] Source priors are implemented

[ ] Historical source reliability is implemented

[ ] Effective source reliability is implemented

[ ] Independence is represented

[ ] Supporting evidence is represented

[ ] Contradicting evidence is represented

[ ] Unresolved evidence is represented

[ ] Support weight is calculated

[ ] Contradiction weight is calculated

[ ] Direction is calculated

[ ] Evidence sufficiency is calculated

[ ] Evidence confidence is calculated

[ ] Confidence is explicitly treated as an evidence-strength index

[ ] Qualitative evidence states exist

[ ] Thresholds have been tested against representative scenarios

[ ] Contradictions remain visible

[ ] Same-source repetition does not count as independent corroboration

[ ] Assessment changes can be explained from structured state

[ ] Hindsight-empty and Hindsight-unavailable states are distinct

[ ] Core calculations are deterministic

[ ] Unit tests pass

[ ] Integration tests cover the major evidence scenarios

[ ] No Groq-generated value controls the score

[ ] No mechanical diagnosis is produced

---

# 52. Scope Boundary

At the end of this stage, VeriCar can deterministically answer:

> "How strong is the available evidence for this finding, and what historical evidence produced that assessment?"

The system still needs a separate explanation layer to turn that structured evidence into concise natural language.

That is:

```
14 — LLM Reasoning & Explanation
```

The architecture remains:

```
Hindsight
   ↓
Historical evidence
   ↓
Deterministic Evidence Engine
   ↓
Structured Assessment
   ↓
Groq
   ↓
Human-readable Explanation
   ↓
Frontend
```

```

This document intentionally leaves the **qualitative thresholds unfrozen** until we run the 6–8 scenarios against the actual formula. That validation is the next engineering task before we treat the scoring model as final.
```
