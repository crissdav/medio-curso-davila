# SPEC-001: Electronic invoice and sales receipt issuance

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-01, UC-02, UC-14, UC-15, UC-17, UC-24, UC-26 · SPEC-003, 004, 005, 006, 007 · ADR-002

## Summary
Issue electronic Invoices (01, *factura*) and Sales receipts (03, *boleta*) valid before SUNAT from
a sale, with automatic tax calculation and controlled numbering.

## Motivation
The current system "does not generate XMLs" nor issues legal documents (RS 097-2012/SUNAT).

## Scope
- **Includes:** domestic sale (0101), PEN/USD currency, cash or credit payment terms with installments,
  printed representation (A4 and ticket), email delivery to the customer, public document lookup
  (UC-24) and Excel document report (UC-15, UC-26).
- **Excludes:** exports, SPOT withholding (*detracción*), prepayments, perception (phase 2).

## Business rules
| ID | Rule |
|---|---|
| R-01 | Invoice: series `F###` and a customer with a valid RUC (catalog 06 = 6) according to SPEC-004. |
| R-02 | Sales receipt: series `B###`; customer with DNI or another catalog 06 document. |
| R-03 | The issue date cannot be in the future nor earlier than the current maximum submission deadline. |
| R-04 | A sales receipt whose total exceeds the current threshold (S/ 700) requires identifying the customer (`-` is not allowed). |
| R-05 | A currency other than PEN requires `exchangeRate`. |
| R-06 | Credit payment terms require `pendingAmount` and at least one installment; Σ installments = pendingAmount; installment dates > issue date (RS N.° 000193-2020/SUNAT, Annex IV, data items 170–173). |
| R-07 | Amounts are always calculated on the server (SPEC-003); totals sent by the client are ignored. |
| R-08 | The printed representation includes a QR code with: RUC, type, series, number, IGV, total, date, customer document type and number, and hash. |
| R-09 | The public lookup (UC-24) requires the exact RUC, type, number, date and total amount, and rate-limits requests per IP, so that other people's documents cannot be enumerated. |
| R-10 | The Excel report (UC-26) filters by date range and establishment, with detail per document or per item, and includes accepted, rejected and voided documents. |

## Acceptance criteria
- **AC-1:** Given a customer with a valid and active RUC, when I issue an invoice with series F001, then I get 201 with number `F001-<sequence>` and status `ACCEPTED` or `OBSERVED`.
- **AC-2:** Given an invoice with a DNI customer, when I issue it, then I get 400 `INVALID_RUC` / schema validation error.
- **AC-3:** Given a S/ 750 sales receipt with customer `-`, when I issue it, then I get 400 `CUSTOMER_REQUIRED_FOR_RECEIPT`.
- **AC-4:** Given a USD sale without an exchange rate, when I issue it, then I get 400.
- **AC-5:** Given a credit invoice whose installments do not add up to the pending amount, when I issue it, then I get 400.
- **AC-6:** Given the example [invoice-request.json](../schemas/examples/invoice-request.json), when I issue it, then the totals match [invoice-response.json](../schemas/examples/invoice-response.json).
- **AC-7:** Given the same `Idempotency-Key` sent twice, then the same document is returned and the sequence number advances only once.
- **AC-8:** Given invoice `F001-123` with a total of 377.81, when I look it up publicly with 377.80, then I get 404; with 377.81 I get 200 and the download links.

## Contracts
- `POST /invoices` · [invoice.schema.json](../schemas/invoice.schema.json)
- `GET /public/invoices` (UC-24) · `GET /reports/invoices` (UC-15, UC-26) · [openapi.yaml](../api/openapi.yaml)

## Edge cases
- Sale with 500 items (maximum).
- Customer legal name with special characters (`&`, `Ñ`) → correct XML escaping.

## Open questions
- Is issuing to customers flagged NO HABIDO (not located) blocked or only warned? (see SPEC-004).
