# SPEC-002: Electronic credit and debit notes

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-03, UC-04 · SPEC-001, 003, 006 · Catalogs 09 and 10

## Summary
Issue Credit Notes (07, UBL `CreditNote`) and Debit Notes (08, UBL `DebitNote`) that modify an
already accepted document.

## Motivation
An accepted document is immutable (INV-06). Later discounts, returns, cancellations, interest or
penalties can only be reflected through notes.

## Business rules
| ID | Rule |
|---|---|
| R-01 | The affected document must exist, belong to the same issuer and be `ACCEPTED` or `OBSERVED`. |
| R-02 | The note series has the same prefix as the affected document: invoice note `F###`, sales receipt note `B###`. |
| R-03 | `noteType` must belong to catalog 09 (credit) or 10 (debit). |
| R-04 | Credit note: Σ credit notes on a document ≤ total amount of the affected document. |
| R-05 | Type 01 (cancellation) or 06 (full return) ⇒ the note replicates all the lines and the affected document becomes `VOIDED`. |
| R-06 | The note currency = the affected document currency. |
| R-07 | A return (06, 07) creates an `INBOUND` inventory movement (SPEC-010). |

## Acceptance criteria
- **AC-1:** Given the accepted invoice `F001-00000123`, when I issue a type 07 credit note for 2 soft drinks, then it is issued with series F001 and an inbound movement of 2 units is recorded.
- **AC-2:** Given a sales receipt, when I issue a note with series `F001`, then I get 400 `SERIES_MISMATCH`.
- **AC-3:** Given a S/ 100 invoice with a previous S/ 80 credit note, when I issue another S/ 30 credit note, then I get 400.
- **AC-4:** Given a debit note with `noteType` = 05, then I get 400 (not in catalog 10).

## Contracts
- `POST /notes` · [note.schema.json](../schemas/note.schema.json) · example [credit-note-request.json](../schemas/examples/credit-note-request.json)

## Open questions
- Maximum period to issue a credit note on a document (check the current regulations).
