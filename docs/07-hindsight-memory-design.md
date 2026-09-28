# VeriCar — Hindsight Memory Design

## 1. Purpose

Hindsight is the persistent memory layer of VeriCar.

Its purpose is to preserve and retrieve meaningful historical context about:

* vehicles
* reports
* observations
* issues
* source histories
* corroboration
* contradictions
* changes over time

The core principle is:

> Hindsight stores historical meaning and context; the application remains responsible for deterministic scoring and current derived state.

Hindsight should not become a second transactional database or an uncontrolled decision-making layer.

---

# 2. Hindsight's Role

The system follows this flow:

```text
                    NEW REPORT
                        |
                        v
                 +-------------+
                 |   Backend   |
                 +------+------+
                        |
             +----------+----------+
             |                     |
             v                     v
      +--------------+      +--------------+
      |   Vehicle    |      |    Source    |
      |    Memory    |      |    Memory    |
      +------+-------+      +------+-------+
             |                     |
             +----------+----------+
                        |
                        v
                +---------------+
                |    Evidence   |
                |     Engine    |
                +-------+-------+
                        |
                        v
                +---------------+
                |     Score     |
                |     Engine    |
                +-------+-------+
                        |
                        v
                +---------------+
                |      Groq     |
                |  Explanation  |
                +---------------+
```

Hindsight's responsibility is primarily:

```text
remember -> retrieve -> provide context
```

It should not be responsible for:

```text
remember -> independently decide everything
```

---

# 3. Logical Memory Scopes

VeriCar uses two logical memory scopes.

```text
Vehicle Memory
    vehicle:{vehicle_id}

Source Memory
    source:{source_id}
```

These are logical identifiers for the application design.

The exact Hindsight API, namespace, and SDK syntax must follow the actual Hindsight implementation documentation during development. The application must not invent unsupported Hindsight APIs.

---

# 4. Vehicle Memory

Vehicle memory answers:

> "What has historically been reported about this vehicle?"

Example logical identity:

```text
vehicle:VEH-001
```

Vehicle memory should preserve meaningful historical events such as:

* report submissions
* observations
* inspections
* mechanic findings
* buyer observations
* recurring issues
* corroboration
* contradictions
* changes in assessment context

---

# 5. Example Vehicle Memories

Example memory 1:

```text
Vehicle: VEH-001

Date: 2026-01-10
Source: SRC-001
Source type: owner

The owner reported that the vehicle was operating
normally and reported no known transmission issues.
```

Example memory 2:

```text
Vehicle: VEH-001

Date: 2026-03-04
Source: SRC-002
Source type: inspector

An independent inspection reported a hard 2->3 shift
during operation.
```

Example memory 3:

```text
Vehicle: VEH-001

Date: 2026-04-19
Source: SRC-003
Source type: mechanic

An independent mechanic reported transmission
hesitation during a test drive.
```

These memories preserve the meaning of the reports rather than only storing report identifiers.

---

# 6. Vehicle Memory Payload

Each historical vehicle event should contain enough context to identify:

```text
WHO
  |
  v
WHAT
  |
  v
WHEN
  |
  v
WHICH VEHICLE
  |
  v
WHICH ISSUE
```

Conceptually:

```json
{
  "vehicle_id": "VEH-001",
  "report_id": "RPT-003",
  "source_id": "SRC-003",
  "source_type": "mechanic",
  "date": "2026-04-19",
  "issue": "transmission_shift_behavior",
  "observation": "Transmission hesitation confirmed during test drive.",
  "relationship_context": "supports previous inspector observation"
}
```

The exact representation passed to Hindsight depends on the actual Hindsight API.

---

# 7. Preserve the Original Report

Hindsight memory must not replace the original report.

The system should preserve:

```text
Original Report
        +
Structured Interpretation
        +
Persistent Memory
```

Example:

```text
Original:
"Hard 2->3 shift observed during inspection."

Structured:
issue_candidate = transmission_shift_behavior

Memory:
Independent inspector reported transmission
shift behavior on 2026-03-04.
```

This provides traceability from the current assessment back to the original evidence.

---

# 8. Source Memory

Source memory answers:

> "What do we know about this source's historical reporting behavior?"

Example logical identity:

```text
source:SRC-003
```

Example source context:

```text
Source: SRC-003
Type: mechanic

Historical reports:
18 resolved
14 corroborated
2 contradicted
2 unresolved
```

However, source memory should not consist only of a continuously overwritten reliability number.

Historical events should be preserved.

---

# 9. Source Memory Events

Example:

```text
2026-02-01

SRC-003 reported brake noise.
Later corroborated by an inspector.
```

```text
2026-03-12

SRC-003 reported engine vibration.
Later contradicted by inspection.
```

```text
2026-04-19

SRC-003 reported transmission hesitation.
Currently unresolved.
```

The backend can derive:

```text
corroborated = 14
contradicted = 2
unresolved = 2
```

from the historical record.

---

# 10. Why Event-Based Memory Matters

Avoid making a derived value such as:

```text
reliability = 91%
```

the fundamental memory.

If memory only contains:

```text
reliability = 91%
```

the system cannot explain how that value was produced.

If memory contains historical events:

```text
Report A -> corroborated
Report B -> corroborated
Report C -> contradicted
Report D -> unresolved
...
```

the backend can reconstruct and recalculate the source reliability.

Therefore:

> Historical events are more authoritative than derived scores.

---

# 11. What Should Not Be Primary Memory

The following should not be treated as fundamental historical memory:

```text
vehicle confidence = 86%
source trust = 91%
AI thinks this vehicle is risky
final verdict = bad
```

These are derived outputs.

The system should primarily remember:

```text
who reported what
when it was reported
which vehicle it concerned
which issue it concerned
what later evidence supported it
what later evidence contradicted it
```

---

# 12. Memory Lifecycle

Every report follows this conceptual lifecycle:

```text
REPORT
   |
   v
Validate Input
   |
   v
Store Original Report
   |
   v
Write Vehicle Memory
   |
   v
Write Source Memory
   |
   v
Retrieve Relevant Historical Memories
   |
   v
Evidence Engine
   |
   v
Recalculate Derived State
   |
   v
Current Finding
```

---

# 13. Retrieval Before Scoring

This is a core architectural rule.

When a new report arrives:

```text
NEW REPORT
    |
    v
Retrieve relevant vehicle memory
    |
    v
Retrieve relevant source memory
    |
    v
Combine historical context with current report
    |
    v
Evidence analysis
    |
    v
Confidence calculation
```

The system should not calculate the final assessment before retrieving historical memory.

Otherwise, Hindsight would not materially influence the reasoning process.

---

# 14. Vehicle Memory Retrieval

Suppose a new report says:

```text
"Transmission hesitates when moving from second
to third gear."
```

The backend should retrieve relevant historical vehicle memories.

Potential results:

```text
Inspector:
"Hard 2->3 shift observed."

Mechanic:
"Transmission hesitation."

Owner:
"No transmission problems."
```

The evidence engine now has historical context instead of evaluating the new report in isolation.

---

# 15. Source Memory Retrieval

The backend should also retrieve the submitting source's historical context.

For example:

```text
SRC-003
Mechanic

Previous reporting record:
18 resolved reports
14 corroborated
2 contradicted
2 unresolved
```

This historical context contributes to the source reliability calculation.

---

# 16. Retrieval Should Be Relevant

The backend should not blindly retrieve the entire vehicle history for every report.

For a transmission-related report, relevant memories may include:

```text
transmission
gearbox
shifting
2->3 shift
hesitation
delayed engagement
```

Unrelated memories may include:

```text
paint scratch
seat tear
air-conditioning noise
```

Relevant semantic retrieval is therefore important.

---

# 17. Semantic Retrieval

Exact phrase matching is insufficient.

For example:

```text
"transmission hesitation"
```

and:

```text
"hard 2->3 shift"
```

may describe related underlying behavior even though the wording differs.

Hindsight's semantic memory capabilities should help retrieve conceptually related observations.

The backend can then normalize those observations into structured issue candidates for deterministic evidence analysis.

---

# 18. Contradictory Memories Must Also Be Retrieved

Retrieval must not only search for memories supporting the newest claim.

Suppose the new report says:

```text
"Transmission works perfectly."
```

The system should still retrieve relevant historical observations:

```text
Owner:
"Transmission works perfectly."

Inspector:
"Hard 2->3 shift."

Mechanic:
"Transmission hesitation."
```

The evidence engine must receive both supporting and contradictory information.

Contradictions must remain visible rather than being averaged away.

---

# 19. Memory Categories

Vehicle memory can be conceptually organized around:

```text
REPORT
OBSERVATION
ISSUE
CORROBORATION
CONTRADICTION
HISTORY
```

Source memory can be conceptually organized around:

```text
SOURCE PROFILE
REPORT HISTORY
CORROBORATION EVENT
CONTRADICTION EVENT
RESOLUTION EVENT
```

These are conceptual categories, not necessarily separate Hindsight databases.

---

# 20. Memory Metadata

Every memory event should contain enough information for traceability.

At minimum:

```text
vehicle_id
source_id
report_id
date
source_type
issue_candidate
```

Where supported by the actual Hindsight API, structured metadata should be used rather than placing every field only inside free-form text.

---

# 21. Traceability

Every current finding should be traceable through:

```text
Finding
   |
   v
Evidence
   |
   v
Report
   |
   v
Source
```

Memory should provide the reverse historical path:

```text
Memory
   |
   v
Report ID
   |
   v
Original Report
```

Therefore:

> No important historical statement should exist without an identifier connecting it to the underlying report.

---

# 22. Hindsight and Application Data

Hindsight is the memory layer.

The application's structured data layer is the authoritative transactional layer.

Conceptually:

```text
APPLICATION DATA
----------------
Vehicle
Source
Report
Claim
Evidence
Finding
```

versus:

```text
HINDSIGHT
---------
Historical context
Meaningful observations
Cross-time relationships
Source history
Relevant remembered information
```

The system should not duplicate every database field into Hindsight.

---

# 23. Why Both Layers Exist

Structured application data is responsible for:

```text
exact IDs
exact dates
exact relationships
exact counts
deterministic calculations
API responses
```

Hindsight is responsible for:

```text
historical context
semantic retrieval
cross-time relationships
meaningful recollection
```

This separation provides both precision and persistent memory.

---

# 24. Scoring Must Use Structured Facts

Even when Hindsight retrieves useful historical context, the deterministic scoring engine should ultimately operate on structured evidence.

For example, Hindsight may retrieve:

```text
"Inspector previously reported hard 2->3 shifting."
```

The backend resolves that historical memory back to:

```text
report_id = RPT-002
source_id = SRC-002
source_type = inspector
date = 2026-03-04
```

The scoring engine then uses:

```text
source reliability
independence
date
evidence relationship
```

This prevents the LLM or memory layer from becoming an uncontrolled scoring mechanism.

---

# 25. Groq's Position

Groq operates after memory retrieval and evidence preparation.

```text
Hindsight
   |
   v
Relevant Memories
   |
   v
Structured Evidence
   |
   v
Deterministic Scoring
   |
   v
Groq
   |
   v
Human-Readable Explanation
```

Groq receives relevant evidence context and explains the result.

It does not independently determine the evidence confidence score.

---

# 26. Example Complete Flow

A new report arrives:

```text
Source:
SRC-005

Source type:
buyer

Report:
"I experienced hard shifting between second
and third gear during my test drive."
```

### Step 1 — Validate

The backend validates the report.

### Step 2 — Store

Create:

```text
RPT-005
```

### Step 3 — Write Vehicle Memory

Store a historical event such as:

```text
Buyer SRC-005 reported hard shifting between
second and third gears on VEH-001.
```

### Step 4 — Write Source Memory

Store:

```text
SRC-005 submitted a buyer report concerning
transmission shift behavior for VEH-001.
```

### Step 5 — Retrieve Vehicle Memory

Hindsight may retrieve:

```text
Inspector:
hard 2->3 shift

Mechanic:
transmission hesitation

Owner:
no transmission issues
```

### Step 6 — Retrieve Source History

If the buyer has previous reports, retrieve relevant source history.

For example:

```text
2 previously corroborated
1 unresolved
```

### Step 7 — Build Evidence

The evidence engine identifies:

```text
Supporting:
RPT-002
RPT-003
RPT-005

Contradicting:
RPT-001
```

### Step 8 — Calculate Confidence

The deterministic evidence-confidence model calculates the current evidence strength.

### Step 9 — Generate Explanation

Groq receives the structured evidence and produces an explanation such as:

```text
The assessment increased because a third
independent source reported behavior consistent
with two earlier transmission observations.

Earlier owner reports describing normal operation
remain part of the history.
```

### Step 10 — Display

The frontend displays the updated assessment and allows the user to inspect the underlying evidence.

---

# 27. Memory Write Rules

A report should create persistent memory after it passes validation.

Conceptually:

```text
POST /api/reports
        |
        v
Validate
        |
        +---- invalid -> reject
        |
        v
Persist Report
        |
        v
Write Vehicle Memory
        |
        v
Write Source Memory
```

Malformed or rejected reports must not become persistent historical evidence.

---

# 28. Memory Update Rules

When new evidence arrives:

```text
New Report
    |
    v
Retrieve Relevant Memory
    |
    v
Identify Relationships
    |
    v
Calculate Evidence
    |
    v
Update Derived State
```

Historical memories should not be rewritten merely because the current assessment changes.

Historical memory represents what was reported.

The current assessment represents the latest derived interpretation.

---

# 29. What Hindsight Should Remember Over Time

The most important information is:

```text
WHO
WHAT
WHEN
WHICH VEHICLE
WHICH ISSUE
WHAT HAPPENED AFTERWARD
```

Example:

```text
Who:
Independent mechanic SRC-003

What:
Reported transmission hesitation

When:
2026-04-19

Vehicle:
VEH-001

Issue:
Transmission shift behavior

What happened afterward:
A later buyer independently reported hard shifting.
```

The final relationship is where persistent memory becomes especially valuable.

---

# 30. Hindsight Design Principle

Hindsight should not be treated as:

```text
"storage for old chatbot messages"
```

It should be treated as:

```text
LONGITUDINAL MEMORY OF VEHICLE AND SOURCE HISTORY
```

This distinction should be reflected in the README, architecture documentation, and demo.

---

# 31. V1 Memory Contract

The Hindsight layer must satisfy the following requirements:

```text
[ ] Vehicle-specific persistent memory

[ ] Source-specific persistent memory

[ ] Historical reports remain retrievable

[ ] Semantically related reports can be recalled

[ ] Contradictory reports remain retrievable

[ ] Memory is linked back to report IDs

[ ] New reports trigger memory retrieval

[ ] Retrieved memory influences evidence analysis

[ ] Historical memory is not overwritten by current findings

[ ] Derived scores are not treated as primary memory

[ ] Hindsight failures are distinguishable from empty history
```

---

# 32. Hindsight Failure Handling

Hindsight failure must never be interpreted as:

```text
"No history found."
```

These are different states.

### Empty history

```text
Hindsight responded successfully.
No relevant memories exist.
```

### Memory unavailable

```text
Hindsight could not be reached or returned an error.
```

The UI must distinguish them.

Example:

```text
No history found
```

means:

> The system searched successfully and found no relevant historical evidence.

Whereas:

```text
Historical memory temporarily unavailable
```

means:

> The system could not reliably retrieve memory.

The second state must never produce a false "clean history" result.

---

# 33. Strong Hindsight Demonstration

A strong demonstration should show memory changing the assessment over time.

### State 1

```text
VIN-001

No history.
```

Assessment:

```text
Insufficient evidence
```

### State 2

Add:

```text
Owner:
"Car runs perfectly."
```

Assessment remains cautious.

### State 3

Add:

```text
Inspector:
"Hard 2->3 shift."
```

The system retrieves the earlier owner report and identifies conflicting observations.

### State 4

Add:

```text
Mechanic:
"Transmission hesitation confirmed."
```

The system retrieves:

```text
Owner
+
Inspector
+
Mechanic
```

The evidence base becomes stronger because independent observations have accumulated over time.

The important demonstration is not simply the final score.

It is:

> **The system remembers what happened before and uses that history when interpreting what happens now.**

---

# 34. Architectural Principle

The central VeriCar memory loop is:

```text
PERSIST
   |
   v
RETRIEVE
   |
   v
COMPARE
   |
   v
CORROBORATE / CONTRADICT
   |
   v
CALCULATE
   |
   v
EXPLAIN
   |
   v
PERSIST NEW CONTEXT
```

This loop is what makes Hindsight load-bearing rather than decorative.

---

# 35. Implementation Boundary

Before implementation, the following must be verified against the actual Hindsight API:

* memory creation/write operation
* memory retrieval/search operation
* memory identity or namespace mechanism
* metadata support
* retrieval filtering
* response format
* authentication
* error behavior
* available local/deployed configuration

The implementation must use the actual supported Hindsight API rather than invented method names or assumptions.

---

# 36. Final Design Summary

VeriCar uses Hindsight as a persistent longitudinal memory system.

```text
Vehicle Memory
        +
Source Memory
        |
        v
Historical Context
        |
        v
Relevant Retrieval
        |
        v
Structured Evidence
        |
        v
Deterministic Evidence Engine
        |
        v
Current Assessment
        |
        v
Groq Explanation
```

The application database remains authoritative for structured transactional data.

Hindsight preserves and retrieves historical context.

The scoring engine remains deterministic.

Groq explains rather than invents evidence.

Contradictions remain visible.

Derived scores remain derived.

Historical evidence remains traceable.

The result is a system in which the vehicle's assessment can genuinely evolve as new evidence accumulates over time.
