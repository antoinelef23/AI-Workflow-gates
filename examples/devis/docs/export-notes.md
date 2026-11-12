# Quote export — preparatory notes

> ⚠️ **Historical note (T1, written before OQ-1 was resolved).** Since spec v1.0.0,
> OQ-1 is resolved: **plain text** export via `format_quote` (PDF = phase 2). The content
> below reflects the state at the time of writing, kept for the audit trail.

The export-devis spec (v0.9.0) is validated but **OQ-1 remains open**: the contractual
export format (PDF, CSV, or both) has not been decided by the business.
As long as OQ-1 is not resolved, the export module (BHV-1, EVAL-1) is blocked.

Options: **PDF** (readable contractual document, handed to the client) or **CSV**
(structured data, reusable in a spreadsheet or a third-party IS).
Decision criteria for the sponsor: intended client use (reading vs reprocessing),
expected contractual value, implementation and maintenance cost.
Whatever the format, the "estimate" mention is required (INV-1).
