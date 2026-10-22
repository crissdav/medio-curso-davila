# SPEC-004: Customer identity validation (RUC / DNI)

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-05 · Catalog 06 · SPEC-001

## Summary
Validate the format and check digit of identity documents, and look up the taxpayer's status and
condition in the RUC registry.

## Motivation
The current system "does not validate RUCs": invoices are issued to non-existent RUCs, which SUNAT rejects.

## Business rules
| ID | Rule |
|---|---|
| R-01 | **RUC**: 11 digits, prefix `10`, `15`, `16`, `17` or `20`, and a **modulus 11** check digit: weights `5,4,3,2,7,6,5,4,3,2` over the first 10 digits; `r = 11 − (Σ mod 11)`; if `r = 10` → `0`, if `r = 11` → `1`; `r` must equal the 11th digit. |
| R-02 | **DNI**: 8 numeric digits. Other documents: catalog 06 pattern. |
| R-03 | Registry lookup: if status ≠ `ACTIVO` or condition = `NO HABIDO` (not located) → warning `CUSTOMER_NOT_LOCATED` (blocking configurable by the company). |
| R-04 | The registry is queried through a local cache (24 h TTL); if the external service fails, the last known data is used with `source = LOCAL_REGISTRY`. |
| R-05 | Format and modulus 11 validation also run on the client (`shared` module) for immediate feedback; the server always repeats it. |

## Acceptance criteria
- **AC-1:** RUC `20123456786` → valid. RUC `20123456787` → `INVALID_RUC`.
- **AC-2:** RUC `30123456786` → invalid prefix.
- **AC-3:** DNI `1234567` → invalid (7 digits).
- **AC-4:** Given a RUC with condition NO HABIDO and a "warn" policy, when I issue an invoice, then it is issued and the response includes the warning.
- **AC-5:** Given the registry service is down, when I look up a cached RUC, then I respond 200 with `source = LOCAL_REGISTRY`.

## Contracts
- `GET /taxpayers/{ruc}`, `POST /identity-documents/validations` · [customer.schema.json](../schemas/customer.schema.json)
