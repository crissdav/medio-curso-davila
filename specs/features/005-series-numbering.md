# SPEC-005: Series and sequence numbers

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-11 · INV-05 · SPEC-001, 002

## Summary
Manage series per document type and establishment, and assign unique, consecutive, non-reusable
sequence numbers.

## Business rules
| ID | Rule |
|---|---|
| R-01 | Series = 4 alphanumeric characters: `F` + 3 for invoices and their notes; `B` + 3 for sales receipts and their notes. |
| R-02 | Documents are only issued with series registered and active for that type and establishment → otherwise `SERIES_NOT_AUTHORIZED`. |
| R-03 | Sequence number from 1 to 99 999 999, unique per (RUC, type, series). When the maximum is reached a new series is required. |
| R-04 | Atomic assignment (pessimistic lock on the series row) within the issuing transaction. |
| R-05 | An assigned sequence number is **never** reused, not even if SUNAT rejects the document. |
| R-06 | A repeated `Idempotency-Key` returns the already created document without assigning a new sequence number. |
| R-07 | Legacy numbers (`nro_documento`) are **not** loaded as SUNAT sequence numbers (SPEC-009). |

## Acceptance criteria
- **AC-1:** Given 50 concurrent issues on F001, then 50 distinct sequence numbers without gaps are assigned.
- **AC-2:** Given a rejected document with number 10, then the next issue gets 11.
- **AC-3:** Given series `X001`, then creation returns 400.

## Contracts
- `GET/POST /series` · `Series` in [openapi.yaml](../api/openapi.yaml)
