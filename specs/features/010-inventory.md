# SPEC-010: Inventory integrated with sales

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-10, UC-16, UC-25 · SPEC-002, 008, 009

## Summary
Keep the current warehouse functionality (inbound and outbound movements) and connect it with
invoicing: every accepted sale decreases stock and every return or voiding restores it.

## Rules
| ID | Rule |
|---|---|
| R-01 | The `InvoiceAccepted` (or `OBSERVED`) event creates an `OUTBOUND` movement per goods line (not `ZZ` services), with `documentReference.type = INVOICE`. |
| R-02 | Credit notes type 06/07 and confirmed voidings create an `INBOUND` movement. |
| R-03 | A `REJECTED` document does not move stock. |
| R-04 | Movements are immutable; corrections are made with an `ADJUSTMENT` with a reason. |
| R-05 | The stock ledger shows `NEW` and `LEGACY` movements on a single timeline. |
| R-06 | The product defines its tax configuration (IGV affectation, ISC catalog 08, ICBPER), proposed by default on the sale. |
| R-07 | Sale with insufficient stock: configurable warning (it does not block tax issuance). |
| R-08 | Phase 1: purchase inbound movements are recorded as manual `INBOUND` movements. Formal purchase and supplier recording (UC-25), which will create them automatically, is specified in phase 2. |

## Acceptance criteria
- **AC-1:** Given the accepted reference invoice, then the stock of `CER-620` decreases by 12.
- **AC-2:** Given the credit note in [credit-note-request.json](../schemas/examples/credit-note-request.json), then the stock of `GAS-3L` increases by 2.
- **AC-3:** Given a migrated product with `requiresReview = true`, when I try to sell it, then I am asked to confirm its tax configuration.

## Contracts
- `GET/POST /products`, `GET/POST /inventory/movements` · [product.schema.json](../schemas/product.schema.json) · [inventory-movement.schema.json](../schemas/inventory-movement.schema.json)
