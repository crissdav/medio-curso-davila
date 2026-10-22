# SPEC-008: Daily summary of sales receipts and voiding communication

- **Status:** Draft (skeleton — detailed in phase 2)
- **Date:** 2026-10-22
- **Related:** UC-07, UC-08 · SPEC-007 · [voided-documents.schema.json](../schemas/voided-documents.schema.json)

## Summary
Build and submit asynchronously (`sendSummary` → ticket → `getStatus`):
- **Daily summary (RC)**: reports the sales receipts and their notes of one day.
- **Voiding communication (RA, *comunicación de baja*)**: voids accepted documents that should not have been issued.

## Rules
| ID | Rule |
|---|---|
| R-01 | Identifier: `RC-YYYYMMDD-n` / `RA-YYYYMMDD-n` (n = daily sequence). |
| R-02 | The scheduler builds the previous day's RC automatically; it can also be triggered manually. |
| R-03 | A sales receipt already reported individually is not included again in an RC as "add". |
| R-04 | Voiding only applies to ACCEPTED/OBSERVED documents, within the current deadline, and not if the goods were already delivered (in that case: credit note type 01). |
| R-05 | When the ticket is confirmed, the voided documents become `VOIDED` and stock is reverted (SPEC-010). |
| R-06 | Deadlines (RC submission, voiding) are parameters with effective periods. Reference value for voiding: **7 calendar days** from issuance; after that, a credit note is issued (per Nubefact's help center, see [use cases §7](../../docs/01-use-cases.md)). |

## Acceptance criteria
- **AC-1:** Given 30 sales receipts from 10/21, when the scheduler runs on 10/22, then `RC-20261022-1` is submitted and the ticket is stored.
- **AC-2:** Given a ticket with CDR code 0, then the voided documents become `VOIDED`.
- **AC-3:** Given a voiding request for a `REJECTED` document, then 400.
