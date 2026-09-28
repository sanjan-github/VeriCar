# VeriCar — Trust-Weighted Vehicle History Memory Agent

## 1. Project Overview

VeriCar is a vehicle-history decision-support application built around **persistent memory**.

The core idea is:

> A vehicle should not be evaluated from a single report or a single AI response. Its assessment should evolve as independent reports accumulate over time, while the system also learns how reliable different reporting sources have historically been.

Each vehicle is identified by its VIN and becomes a persistent memory subject.

VeriCar maintains two forms of memory:

1. **Vehicle memory**

   * Reports about the vehicle
   * Issues observed over time
   * Corroborating reports
   * Contradictory reports
   * Dates and observation periods
   * Historical context

2. **Source memory**

   * Historical reports from each source
   * Reports later corroborated
   * Reports later contradicted
   * Unresolved reports
   * Estimated historical reporting reliability

## 2. Product Thesis

> **VeriCar doesn't tell you what happened to a car. It shows you what the accumulated evidence says.**

VeriCar is therefore not intended to provide absolute truth or mechanical diagnosis.

It provides an evidence-based assessment based on the information available to the system.

## 3. Problem

Vehicle information is often fragmented across:

* owners
* previous buyers
* independent mechanics
* vehicle inspectors

A traditional system may simply display these reports individually.

VeriCar instead tries to understand their relationship over time.

Example:

```text
Owner:
"Car runs perfectly."

Owner:
"No known transmission problems."

Inspector:
"Hard 2→3 shift observed."

Mechanic:
"Transmission hesitation confirmed."

Previous buyer:
"Experienced hard shifting during test drive."
```

The value comes from understanding that these reports form a historical evidence pattern.

## 4. Core Product Behavior

The assessment should evolve:

```text
Unknown vehicle
      ↓
Insufficient evidence
      ↓
Initial owner reports
      ↓
Limited evidence
      ↓
Independent inspection
      ↓
Elevated concern
      ↓
Independent mechanic corroboration
      ↓
Stronger evidence
      ↓
Additional independent report
      ↓
Strong accumulated evidence
```

The system should allow the user to see **why** the assessment changed.

## 5. Claim → Evidence → Finding

VeriCar explicitly distinguishes:

### Claim

What someone reported.

```text
"Transmission sometimes hesitates."
```

### Evidence

A claim that contributes to an assessment.

```text
Independent mechanic reported transmission hesitation
during inspection.
```

### Finding

A conclusion supported by accumulated evidence.

```text
Repeated evidence of transmission-related issues.
```

A user report must never automatically become an established fact.

## 6. Core Differentiator

The innovation is not simply:

> "AI reads vehicle reports."

The important combination is:

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
Transparent confidence
```

The same report can have different significance depending on:

* who submitted it
* that source's historical reporting record
* other independent reports
* whether the issue recurs
* whether contradictory evidence exists
* when the observations occurred

## 7. Product Philosophy

VeriCar should communicate evidence rather than artificial certainty.

Prefer:

> "The available evidence shows repeated reports consistent with a transmission-related issue."

Avoid:

> "This car definitely has a transmission problem."

Prefer:

> "86% evidence confidence."

Avoid:

> "86% probability the transmission is damaged."

The confidence value represents the strength of available evidence, not a verified probability of mechanical failure.

## 8. Intended V1 Scope

V1 focuses on:

* VIN lookup
* persistent vehicle history
* persistent source history
* report submission
* evidence accumulation
* corroboration
* contradiction
* source reliability
* evidence confidence
* transparent explanations

V1 does not attempt to become:

* a vehicle marketplace
* an insurance platform
* an RTO integration
* a dealership platform
* a complete vehicle diagnostic system
* a payment platform
* a social network

Synthetic data will be used for the demonstration.

## 9. Final Product Principle

Everything in VeriCar should support one idea:

> **A vehicle's history becomes more useful as relevant evidence accumulates over time.**

And:

> **A report becomes more informative when interpreted in the context of the source's historical reporting behavior.**
