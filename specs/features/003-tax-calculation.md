# SPEC-003: Tax calculation (IGV, ISC — catalog 08, ICBPER) and totals

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-01, UC-02, UC-18 · Catalogs 05, 07, 08, 16 · INV-04, INV-08, INV-10

## Summary
Pure domain service (`TaxCalculator`) that, from the sale lines, calculates the per-line amounts
and the document totals.

## Motivation
The current system "does not calculate taxes correctly", and a grocery business mixes taxed and
exempt products, products with ISC and bags with ICBPER (see [00-context](../../docs/00-context.md)).

## Parameters (with effective periods, not constants)
| Parameter | Reference value | Source |
|---|---|---|
| IGV rate (incl. IPM) | 0.18 | TUO of the IGV and ISC Law |
| ICBPER per bag | S/ 0.50 | Law 30884 (value in force since 2023) |
| ISC rates / amounts | Per product | Appendices III and IV of the TUO of the IGV and ISC Law |

## Calculation rules (mandatory order)
| ID | Rule |
|---|---|
| R-01 | `saleValue = round2(quantity × unitValue − discount)` |
| R-02 | **ISC according to catalog 08**: <br>• `01` ad valorem: `iscAmount = saleValue × rate` <br>• `02` fixed amount: `iscAmount = quantity × fixedAmount` <br>• `03` retail price: `iscAmount = quantity × (retailPrice / (1 + igvRate)) × rate` |
| R-03 | `igvBase = saleValue + iscAmount` (ISC **is part** of the IGV base). |
| R-04 | IGV according to catalog 07: codes `10`/`17` → `igv = round2(igvBase × igvRate)`; `20`, `30`, `40` → `igv = 0`. |
| R-05 | If the line has `isc`, it must carry the parameter of the chosen system (01 → rate; 02 → fixedAmount; 03 → rate + retailPrice). Otherwise: `ISC_CONFIG_INCOMPLETE`. |
| R-06 | `icbper = bagCount × currentIcbperAmount` (not part of the IGV base). |
| R-07 | Free-of-charge operations (affectation 11–16, 21, 31–37): `unitValue` is a reference value; reported with catalog 16 code `02`; **not added to the total payable**; accumulated in `freeTotal` (tax 9996). |
| R-08 | `unitPrice = (saleValue + iscAmount + igv) / quantity` (catalog 16 code `01`). |
| R-09 | Totals: `taxedTotal = Σ saleValue (affectation 10, 17)`; `exemptTotal = Σ (20)`; `unaffectedTotal = Σ (30)`; `igvTotal = round2(Σ taxed igvBase × igvRate)`; `payableAmount = saleValueTotal + iscTotal + igvTotal + icbperTotal − globalDiscount`. The difference between Σ line IGV and the global IGV must not exceed ±1.00; otherwise → `TOTALS_MISMATCH`. |
| R-10 | Precision: calculation with `BigDecimal`, HALF_UP rounding to 2 decimals for amounts and up to 10 for unit values. |

## Reference example (groceries)
See [invoice-response.json](../schemas/examples/invoice-response.json). ISC rate values are
**illustrative**:

| Item | Cat. 08 | Sale value | ISC | IGV base | IGV | ICBPER |
|---|---|---|---|---|---|---|
| Rice 5 kg × 10 | — | 200.00 | 0.00 | 200.00 | 36.00 | — |
| Beer × 12 | 02 (S/ 1.25 each) | 48.00 | 15.00 | 63.00 | 11.34 | — |
| Soft drink 3 L × 6 | 01 (17 %) | 48.00 | 8.16 | 56.16 | 10.11 | — |
| Bag × 2 | — | 0.17 | 0.00 | 0.17 | 0.03 | 1.00 |
| **Total** | | **296.17** | **23.16** | **319.33** | **57.48** | **1.00** |

Total payable = 296.17 + 23.16 + 57.48 + 1.00 = **377.81**.

## Acceptance criteria
- **AC-1:** Given the reference example, when I calculate, then I get exactly the amounts in the table.
- **AC-2:** Given a line with ISC system 02 without `fixedAmount`, then 400 `ISC_CONFIG_INCOMPLETE`.
- **AC-3:** Given an exempt line (20), then `igv = 0.00` and it adds to `exemptTotal`.
- **AC-4:** Given a free-of-charge line (15), then it is not added to `payableAmount` and it adds to `freeTotal`.
- **AC-5:** Given an ICBPER rate change with a future effective date, when I issue with an earlier date, then the previous rate applies.

## Contracts
- `POST /taxes/calculations` · [line.schema.json](../schemas/line.schema.json) · `Totals` in [invoice.schema.json](../schemas/invoice.schema.json)
