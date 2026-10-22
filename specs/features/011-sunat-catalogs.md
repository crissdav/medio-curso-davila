# SPEC-011: SUNAT catalogs

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** SUNAT Annex 8 · [specs/catalogs/](../catalogs/) · [catalog.schema.json](../schemas/catalog.schema.json)

## Summary
Single, versioned source of the official SUNAT codes used in validations, calculation and XML.
Each code carries an English `description` and its official Spanish `officialName`.

## Catalogs included in phase 1
| No. | Name | Main usage |
|---|---|---|
| 01 | Document type | UBL root, series prefix |
| 02 | Currency (ISO 4217) | `currencyID` on every amount |
| 03 | Unit of measure (UN/ECE Rec 20) | `unitCode` on quantities |
| 05 | Taxes | `TaxScheme` (IGV 1000, ISC 2000, ICBPER 7152, EXO 9997…) |
| 06 | Identity document | Customer `schemeID`; SPEC-004 validation |
| 07 | IGV affectation | Per-line `TaxExemptionReasonCode` |
| **08** | **ISC calculation system** | Per-line `TierRange`; SPEC-003 R-02 formula |
| 09 | Credit note type | `DiscrepancyResponse/ResponseCode` |
| 10 | Debit note type | `DiscrepancyResponse/ResponseCode` |
| 16 | Price type | `PricingReference/PriceTypeCode` |
| 51 | Operation type | `InvoiceTypeCode/@listID` |

## Rules
| ID | Rule |
|---|---|
| R-01 | Every code used in DTOs, calculation or XML must exist in its catalog (checked in CI by `scripts/validate.mjs` and `scripts/validate-sunat-xml.mjs`). |
| R-02 | Catalogs are versioned with effective periods (`validFrom`, `validTo`) in the database; the repository JSON files are the initial seed. |
| R-03 | Codes with `phase: 2` exist but are rejected when issuing in phase 1. |
| R-04 | Catalog 07 defines which tax (catalog 05) corresponds to each affectation. |

## Acceptance criteria
- **AC-1:** `GET /catalogs/08` returns the 3 ISC calculation systems.
- **AC-2:** Given a line with affectation `99`, then 400.
- **AC-3:** Given an issue with operation type `0200` in phase 1, then 400.
