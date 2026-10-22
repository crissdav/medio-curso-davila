# 00 — Context, scope and regulatory basis

## 1. Case

**ABC Software Corp** sells groceries and general merchandise wholesale and retail. Its current
software only records the warehouse's day-to-day activity through informal records:

| Legacy field | Meaning |
|---|---|
| `fecha` | Movement date |
| `ingreso` | Quantity received into the warehouse |
| `salida` | Quantity shipped out of the warehouse |
| `producto` | Free-text product name (no code) |
| `nro_documento` | **Internal** document number (not a SUNAT document) |

### Gaps against the regulations

| Gap | Consequence | Spec that solves it |
|---|---|---|
| Does not validate RUCs | Invoices issued to non-existent taxpayers or with an invalid check digit → rejection | SPEC-004 |
| Does not calculate IGV / ISC / ICBPER | Wrong totals → SUNAT rejection or tax contingency | SPEC-003 |
| Does not generate UBL XML | No legal electronic document exists | SPEC-001, SPEC-002, SPEC-006 |
| Does not sign digitally | The XML has no legal validity | SPEC-006 |
| Does not communicate with an OSE / SUNAT | The document is never validated (no CDR) | SPEC-007, SPEC-008 |
| Does not control sequence numbers | Duplicates or numbering gaps | SPEC-005 |
| Informal historical data | Loss of traceability (RS 234-2006) | SPEC-009, SPEC-010 |

## 2. Scope of this phase (Spec-First skeleton)

**In scope**

- Documents with a detailed contract: Invoice (01, *factura*), Sales receipt (03, *boleta*), Credit note (07), Debit note (08).
- Documents with a use case and endpoint but no detailed schema: Daily summary (RC), Voiding communication (RA).
- Key validations: RUC (modulus 11), DNI, series and sequence numbers, 18 % IGV, ISC (catalog 08), ICBPER, totals reconciliation.
- Migration of the legacy warehouse data.
- Monolithic MVC architecture ready for Hexagonal / microservices.

**Out of scope (phase 2 or later)**

- Electronic dispatch guide (DespatchAdvice) — listed as a use case.
- Withholdings (20), perceptions (40), SPOT withholdings (*detracciones*) with a Banco de la Nación account, prepayments, exports.
- Full catalog of SUNAT validation rules (error codes 2xxx / 3xxx / 4xxx one by one).
- Implementation (code).

## 3. Regulatory basis

| Regulation | What it requires | Design impact |
|---|---|---|
| **RS N° 097-2012/SUNAT** | Creates the Electronic Issuance System developed from the taxpayer's own systems (SEE – Del Contribuyente). | The system builds, signs and submits the XML. Drives SPEC-006/007. |
| **RS N° 234-2006/SUNAT** | Rules on tax-related books and records. | Formal, unalterable and traceable records → audit trail and migration with origin (SPEC-009). |
| [**RS N.° 000193-2020/SUNAT**](https://www.sunat.gob.pe/legislacion/superin/2020/193-2020.pdf) | Amends electronic issuance of the invoice and the credit note: **payment terms** information (cash / credit, pending amount, installments). Its [Annex IV](https://www.sunat.gob.pe/legislacion/superin/2020/anexo4-193-2020.pdf) sets the UBL 2.1 tags (`cac:PaymentTerms`, `FormaPago`, `Cuota001`). | Payment terms in the DTO and in the XML (SPEC-001 R-06, matrix T-20 … T-22). |
| Mass-adoption regulations and amendments | Mandatory electronic issuance and submission deadlines. | Configurable deadlines (SPEC-007, SPEC-008). |
| **Annex 8 — SUNAT catalogs** | Official codes: document type, currency, taxes, IGV affectation, ISC, etc. | SPEC-011 and `specs/catalogs/`. |
| **OASIS UBL 2.1** (`UBL-Invoice-2.1.xsd`, `UBL-CreditNote-2.1.xsd`, `UBL-DebitNote-2.1.xsd`) | XML structure of the document. | SPEC-006 and traceability matrix. |
| SUNAT UBL 2.1 XML guides | Peruvian customization of UBL (`CustomizationID = 2.0`, `PE:SUNAT` attributes). | Traceability matrix. |

> **Why catalog 08 is a "key point":** ABC sells groceries, and that business includes products
> subject to **ISC**: beer and spirits, cigarettes (fixed amount), soft drinks and sugary beverages
> (ad valorem). Catalog 08 defines **how** ISC is calculated (01 ad valorem, 02 fixed amount,
> 03 retail price) and ISC **is part of the IGV base**. An error here carries over into the IGV and the total.

> Note: the current numeric values (18 % IGV rate, S/ 0.50 ICBPER per bag, S/ 700 threshold for
> sales receipts, submission deadlines) are modelled as **parameters with an effective period**,
> not as constants, because they change by regulation.

## 4. Glossary

Peruvian tax terms are kept in their original form; the English equivalent is used in code and contracts.

| Term | Meaning | Name in code |
|---|---|---|
| **RUC** | Peruvian taxpayer ID (11 digits) | `ruc` |
| **IGV** | General Sales Tax (VAT, 18 %) | `igv` |
| **ISC** | Selective Consumption Tax (excise) | `isc` |
| **ICBPER** | Plastic Bag Consumption Tax | `icbper` |
| **Factura** | Invoice (document type 01) | `Invoice`, `documentType = 01` |
| **Boleta de venta** | Sales receipt (document type 03) | `Invoice`, `documentType = 03` |
| **CPE** | Electronic payment document (any of the above) | — |
| **UBL** | Universal Business Language (OASIS), XML standard of the document | — |
| **OSE** | Electronic Services Operator: validates documents on SUNAT's behalf | — |
| **CDR** | Receipt confirmation (*Constancia de Recepción*) from SUNAT/OSE | `Cdr` |
| **Serie / correlativo** | Series / sequence number: `F001-00000001` | `series`, `sequenceNumber` |
| **Valor de venta** | Sale value (before taxes) | `saleValue` |
| **Precio de venta** | Sale price (taxes included) | `unitPrice`, `salePriceTotal` |
| **Afectación del IGV** | IGV affectation (taxed, exempt, unaffected…) | `igvAffectation` |
| **Padrón RUC** / **No habido** | RUC registry / taxpayer not located at its fiscal address | `Taxpayer.condition` |
| **RC / RA** | Daily summary of sales receipts / Voiding communication (*comunicación de baja*) | `daily-summaries`, `voided-documents` |
| **Legacy** | Current warehouse record system | `LEGACY` |
