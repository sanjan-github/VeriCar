# VeriCar — Hackathon Strategy

## 1. Hackathon Context

VeriCar is being developed for the **Hindsight Hackathon**.

The judging criteria are:

| Criterion                | Weight |
| ------------------------ | -----: |
| Innovation               |    30% |
| Hindsight / Memory       |    25% |
| Technical Implementation |    20% |
| UX                       |    15% |
| Real-world Impact        |    10% |

The architecture and demo should therefore make persistent memory a central part of the product rather than an invisible backend dependency.

## 2. Hindsight Must Be Load-Bearing

The project should NOT be:

```text
Normal application
+
LLM
+
Hindsight somewhere in the backend
```

It should be:

```text
Persistent memory
      ↓
Historical evidence
      ↓
Retrieval
      ↓
Cross-time reasoning
      ↓
Evolving assessment
```

The user should be able to see that the current assessment depends on accumulated history.

## 3. Core Demo Story

The demo should use one synthetic vehicle.

Example:

```text
VIN-VERICAR-001
```

### Stage 0 — Unknown

```text
No history found.

There isn't enough evidence to assess this vehicle.

Recommendation:
Obtain an independent inspection.
```

### Stage 1 — Owner Reports

Two owner reports:

```text
"Vehicle runs perfectly."

"No known issues."
```

Result:

```text
LIMITED EVIDENCE

2 reports
2 owner sources

No strong independent corroboration yet.
```

### Stage 2 — Inspector

Inspector reports:

```text
"Hard 2→3 shift observed during inspection."
```

Result:

```text
TRANSMISSION

Elevated concern

3 reports
1 independent high-reliability source
```

The explanation should explicitly state that the assessment changed because an independent inspection introduced a specific transmission observation.

### Stage 3 — Mechanic

Mechanic reports:

```text
"Transmission hesitation confirmed."
```

Result:

```text
Stronger evidence

4 reports
2 independent professional sources
```

### Stage 4 — Previous Buyer

Previous buyer reports:

```text
"Experienced hard shifting during test drive."
```

The system now has multiple independent observations over time.

## 4. The Key Demo Moment

The most important interaction is:

```text
User:
"Why did the assessment change?"
```

VeriCar should explain:

```text
Earlier history contained only owner reports
describing normal operation.

A later independent inspection reported
hard 2→3 shifting.

A mechanic subsequently reported similar
transmission hesitation.

A previous buyer later described the same
behavior.

The assessment increased because independent
observations accumulated over time.
```

This demonstrates:

```text
Persistent memory
+
Retrieval
+
Corroboration
+
Source history
+
Evolving assessment
```

## 5. Submission Materials

The final project should be prepared for:

* GitHub repository
* live project demo
* 2–5 minute demo video
* technical article
* social/video content

## 6. Demo Video

Recommended structure:

```text
0:00–0:20
Problem

0:20–0:50
What VeriCar is

0:50–2:30
Live persistent-memory demonstration

2:30–3:30
Why assessment changed

3:30–4:30
Architecture / Hindsight explanation

4:30–5:00
Limitations and conclusion
```

Use actual application behavior and screen recording.

Avoid cinematic AI-generated filler.

## 7. Technical Article

The article should:

* explain the actual problem
* explain why persistent memory is necessary
* show actual implementation
* include relevant code
* demonstrate before/after behavior
* include screenshots
* acknowledge limitations honestly

Avoid generic promotional AI language.

## 8. Real-World Impact

The intended value is helping users understand fragmented vehicle information and identify issues that may warrant further investigation.

Do not claim that VeriCar:

* guarantees vehicle quality
* detects every hidden defect
* prevents bad purchases
* replaces professional inspection

Prefer:

> VeriCar helps users understand accumulated evidence and identify issues that may warrant further inspection.

## 9. Innovation Story

The innovation is:

```text
Vehicle memory
+
Source memory
+
Evidence accumulation
+
Source reliability history
+
Temporal context
+
Explainable assessment
```

The project should make this combination obvious to judges.

## 10. Hackathon Strategy

The strongest strategy is to build **one tight, polished workflow** rather than many loosely connected features.

The core workflow is:

```text
Search VIN
   ↓
Retrieve memory
   ↓
View current assessment
   ↓
Submit report
   ↓
Store memory
   ↓
Retrieve relevant history
   ↓
Recalculate evidence
   ↓
Assessment changes
   ↓
Explain why
```

The project should optimize for genuine memory behavior, not feature count.
