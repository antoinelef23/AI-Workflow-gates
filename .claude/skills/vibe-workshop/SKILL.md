---
name: vibe-workshop
description: Facilitates the Spec Workshop (105 min, 6-8 people) that produces spec.md v1.0. Use when the PE kicks off a spec workshop with the business — Claude mediates over screen share and writes the spec live.
---

# Spec Workshop — the spec factory

You mediate the workshop over screen share. The business talks, you structure live in the lab/templates/spec.md format. Output goal: spec.md v1.0 committed.

Raw inputs the business brings (slides, transcripts, existing quotes) go in `work/<feature>/assets/` (gitignored — see [ingest-client-assets](../../../docs/how-to/ingest-client-assets.md)); read them to seed the sections below. The committed spec must stand on its own — a decision found only in an asset belongs in the spec.

## Agenda (105 min)
1. **Business intent pitch (15 min)** → §1 Intent + target KPI. Rephrase until explicit agreement.
2. **Digital Event Storming (30 min)** → business events, actors, commands. Feeds §2 Glossary (require a canonical name per term) and the raw list of BHVs.
3. **Invariants & edge-cases sweep (25 min)** → "what must NEVER happen?" → §3 INV-n. Then for each BHV: "what if…?" → edge cases BHV-na, nb…
4. **Examples gallery (25 min)** → §5. Realistic data required (real products, real amounts). Each example tags what it covers. In case of a prose/example disagreement: the example wins.
5. **Wrap-up (10 min)** → review the remaining OQ-n, propose evals (§7) derived from the examples, commit `spec.md v1.0` + tag.

## Facilitation rules
- Ban fuzzy words: "fast", "relevant", "simple" → require a number or an example.
- One question at a time, never technical jargon with the business.
- Any disagreement not settled in session becomes an OQ-n, not a soft compromise.
- The business validates on screen section by section: the spec is THEIR contract.
