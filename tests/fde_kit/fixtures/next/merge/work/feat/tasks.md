---
type: tasks
feature: feat
version: 1.0.0
status: approved
spec: ./spec.md          # version : 1.0.0
design: ./design.md      # version : 1.0.0
---

# Tasks — feat (fixture)

### T1 — First
- **agent:** implementer
- **depends_on:** —
- **parallel_group:** A
- **implements:** [BHV-1]
- **anchored_on:** ADR-1, I-1
- **files_touched:** `src/one.py`
- **prompt:**
  > Implement BHV-1.
- **done_when:** it works
- **verify:** `true`
- **status:** ☐ pending

### T2 — Second
- **agent:** implementer
- **depends_on:** [T1]
- **parallel_group:** B
- **implements:** [INV-1]
- **anchored_on:** ADR-1, I-1
- **files_touched:** `src/two.py`
- **prompt:**
  > Implement INV-1.
- **done_when:** it works
- **verify:** `true`
- **status:** ☐ pending

### CP-1 — CHECKPOINT: merge
- **trigger:** automatic when [T1, T2] are done
- **validator:** Owner
- **mode:** blocking
- **reviews:** everything
