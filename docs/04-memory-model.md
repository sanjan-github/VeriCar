# VeriCar — Memory Model

## 1. Memory Is the Core Product

Hindsight is not an optional storage layer.

Persistent memory is necessary because VeriCar's value comes from relationships across time.

Without persistent memory:

```text
Report A
→ answer

Report B
→ separate answer

Report C
→ separate answer
```

With persistent memory:

```text
Report A
     ↓
remembered

Report B
     ↓
retrieved with A

Report C
     ↓
retrieved with A + B

Assessment evolves
```

## 2. Two Memory Dimensions

VeriCar has two major memory subjects:

```text
Vehicle Memory
      +
Source Memory
```

## 3. Vehicle Memory

A vehicle is identified by VIN.

Vehicle memory contains meaningful historical information about that vehicle.

Example:

```text
VIN-VERICAR-001

2026-01-10
Owner:
"Vehicle runs perfectly."

2026-02-18
Owner:
"Occasional transmission hesitation."

2026-03-04
Independent Inspector:
"Hard 2→3 shift observed."

2026-04-19
Independent Mechanic:
"Transmission hesitation confirmed."

2026-05-02
Previous Buyer:
"Experienced hard shifting during test drive."
```

The purpose is not merely storing a timeline.

The memory should allow the system to retrieve relevant previous observations when a new report arrives.

## 4. Source Memory

Every source can have persistent historical context.

Example:

```text
SOURCE-027

Type:
Mechanic

Reports:
18

Corroborated:
14

Contradicted:
2

Unresolved:
2
```

The source's future reports can therefore be interpreted using its historical reporting record.

## 5. Memory Namespaces / Logical Separation

Conceptually:

```text
vehicle:{vehicle_id}
```

and:

```text
source:{source_id}
```

The exact Hindsight namespace mechanism should follow Hindsight's actual API and capabilities during implementation.

Do not invent Hindsight APIs.

## 6. Vehicle Memory Should Store

Useful historical facts include:

* report date
* source identity
* source type
* original observation
* relevant issue
* previous related reports
* corroboration
* contradiction
* observation duration
* important changes over time

Example memory:

```text
On April 19, 2026, independent mechanic SRC-004
reported transmission hesitation for VIN-VERICAR-001.

This followed an independent inspector report on
March 4, 2026 describing hard 2→3 shifting.

Earlier owner reports described normal operation.
```

## 7. Source Memory Should Store

Useful source history includes:

* source type
* historical report count
* corroborated reports
* contradicted reports
* unresolved reports
* historical reliability estimate
* important historical patterns

Example:

```text
SRC-004 is a mechanic source.

Historical reporting record:
18 resolved reports
14 corroborated
2 contradicted
2 unresolved

The current reliability estimate is based on this
historical reporting record.
```

## 8. Raw Facts vs Derived State

This distinction is important.

### Raw / authoritative data

```text
Vehicle
Source
Report
Claim
```

These represent information that entered the system.

### Derived data

```text
Evidence
Finding
Source reliability
Evidence confidence
Assessment status
```

These can be recalculated.

Therefore:

```text
Reports
   ↓
Evidence
   ↓
Findings
```

If the scoring formula changes later, the original reports remain available.

## 9. Hindsight Should Not Store Only Scores

Do not make memory equivalent to:

```text
VIN-001:
confidence = 86
```

That destroys explainability.

Memory should preserve the historical observations from which the current assessment can be reconstructed.

## 10. Retrieval Principle

When a new report arrives:

```text
New report
    ↓
Identify vehicle
    ↓
Retrieve relevant vehicle history
    ↓
Identify source
    ↓
Retrieve source history
    ↓
Compare new report with previous evidence
    ↓
Update evidence model
```

## 11. Memory Must Change the Result

A successful memory demonstration should show:

```text
Before:

No relevant history
→ insufficient evidence

After new report:

Previous relevant report retrieved
→ evidence updated

After another report:

Earlier evidence + new evidence
→ assessment changes
```

If removing Hindsight would produce essentially the same result, Hindsight is not sufficiently central to the implementation.

## 12. Contradictory Memory

Contradictions must remain in memory.

Example:

```text
Owner:
"Transmission works perfectly."

Inspector:
"Hard 2→3 shift observed."
```

Both remain part of the vehicle history.

The system should not rewrite the earlier claim as though it never existed.

## 13. Repeated Same-Source Reports

Repeated reports from the same source should remain useful historical observations.

However:

```text
3 reports from 1 mechanic
```

does not equal:

```text
3 independent sources
```

Memory must preserve source identity so the evidence engine can make that distinction.

## 14. Synthetic Demo Memory

Development, testing, and demonstration scenarios should use synthetic data.

Example source identities:

```text
SRC-001
SRC-002
SRC-003
```

Example vehicle:

```text
VIN-VERICAR-001
```

This avoids unnecessary collection of real personal information.

## 15. Memory Failure States

The system must distinguish:

### No memory exists

```text
Hindsight successfully searched,
but no relevant history was found.
```

from:

### Memory unavailable

```text
Hindsight could not be reached or returned an error.
```

These are different states and must produce different UI behavior.

## 16. Memory Philosophy

The core principle is:

> **The system should remember what happened in the reporting history, not merely remember the last answer it generated.**

Memory exists to improve future reasoning.
