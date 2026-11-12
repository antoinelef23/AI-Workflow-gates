---
type: spec
feature: <feature-slug>
version: 0.1.0
status: draft            # draft | validated | superseded
owner: <name of the current Owner>
validated_by: <business — name + date, empty while draft>
---

# Spec — <Feature name>

> **The WHAT. The business contract.** This file is the primary prompt for any agent that codes.
> Golden rules to be perfectly understood by an AI:
> 1. Every statement is **testable** and carries a **stable ID** (INV-n, BHV-n, EX-n, EVAL-n) — never reused, never renumbered.
> 2. Zero ambiguity: "fast", "simple", "relevant" are forbidden without a number.
> 3. Concrete examples take precedence over prose: in case of conflict between prose and example, **the example wins** and the prose must be fixed.
> 4. What is not in the spec does not exist. What is out of scope is stated explicitly (§6).

## 1. Intent

*2 to 5 sentences. Why this feature exists, for whom, and which business KPI it moves. This is the section the agent re-reads when it has to make a call.*

**Target KPI:** <metric, current value → target value, horizon>

## 2. Glossary

*Exact business vocabulary. The agent MUST use these terms in the code (class names, fields, events). One term = one definition = one canonical English name for the code.*

| Business term | Canonical name (code) | Definition |
|---|---|---|
| <term> | `<snake_case>` | <unambiguous definition> |

## 3. Invariants

*The rules that are always true, no matter what. Each invariant is verifiable by a test. Format: MUST / MUST NOT.*

- **INV-1** — <The system MUST ... / MUST NOT ...>
- **INV-2** — ...

## 4. Behaviors

*Expected behaviors, Given/When/Then format. A BHV = one observable behavior, not a technical step.*

### BHV-1 — <short title>
- **Given** <precise initial state>
- **When** <user action or event>
- **Then** <observable result, with values>
- **Edge cases:** <numbered list BHV-1a, BHV-1b… with the expected behavior for each>

## 5. Examples

*Gallery of concrete input → output examples, drawn from the Spec Workshop. Realistic data, no foo/bar. This is the section most read by the agents.*

### EX-1 — <nominal case>
```yaml
input:
  <field>: <realistic value>
expected_output:
  <field>: <exact expected value>
covers: [BHV-1, INV-2]
```

### EX-2 — <edge case>
...

## 6. Non-goals

*What this feature does NOT do, even if it looks close. Prevents the agent from hallucinating scope.*

- **NG-1** — <out of scope + why / where it is handled>

## 7. Evals — merge gate

*Each eval is executable (`pytest -m eval`). No green eval, no merge. An eval references the BHVs/INVs it covers. Every BHV and every INV must be covered by at least one eval.*

*Executable convention: an eval = a pytest test marked `@pytest.mark.eval` whose name contains the ID in lowercase (e.g. `test_eval_1_matching_exact`). This is what lets the orchestrator mechanically verify that an eval exists (anti-empty-gate: a green `just evals` with zero evals collected validates NOTHING) and, eventually, eval ↔ spec coverage.*

| ID | Type | Description | Covers | Success threshold |
|---|---|---|---|---|
| EVAL-1 | deterministic | <exact input/output test> | BHV-1, INV-1 | 100% |
| EVAL-2 | llm-judge | <quality criterion judged by an LLM, rubric in appendix> | BHV-2 | ≥ <n>/10 on <m> cases |
| EVAL-3 | property-based | <property verified on generated data> | INV-2 | 100% |

## 8. Open questions

*Unanswered questions. An agent that hits an OQ stops and asks — it does not guess.*

- **OQ-1** — <question> → *(resolved on <date>: <answer>, integrated as BHV-n)*

## 9. Changelog

| Version | Date | Author | Change |
|---|---|---|---|
| 0.1.0 | <date> | Spec Workshop | Created — spec v1 committed |
