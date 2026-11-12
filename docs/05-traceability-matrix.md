# 05 — Regulatory traceability matrix (SUNAT ↔ UBL 2.1 ↔ DTO)

> Exam deliverable 4. **Reference country: Peru** — UBL 2.1 with the SUNAT customization. Each row
> links a **SUNAT requirement** (required data and its catalog) with the **UBL 2.1 element**
> (XPath relative to the `Invoice` / `CreditNote` / `DebitNote` root), the **contract field** (DTO)
> and the **spec** that validates it.
>
> This table is checked automatically by `scripts/validate.mjs`: every DTO path must exist in the
> JSON Schemas and every `cat-NN:code` must exist in `specs/catalogs/`. In addition, the sample XML
> is validated against the OASIS XSD (structure) and against these rows (SUNAT content):
> see [specs/ref/](../specs/ref/README.md).

Prefixes: `cbc:` = CommonBasicComponents, `cac:` = CommonAggregateComponents,
`ext:` = CommonExtensionComponents, `ds:` = XMLDSig. Attribute values such as `listName="Tipo de Documento"`
are literal SUNAT values and are kept in Spanish.

## 1. Document header (Invoice 01 / Sales receipt 03 — `Invoice` root)

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-01 | UBL version | — | `cbc:UBLVersionID` | fixed value `2.1` | (constant) | 006 |
| T-02 | Structure version | — | `cbc:CustomizationID` | value `2.0`; `schemeAgencyName="PE:SUNAT"` | (constant) | 006 |
| T-03 | Digital signature | — | `ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature` | Enveloped XMLDSig | `Invoice.documentHash` | 006 |
| T-04 | Signatory data | — | `cac:Signature/cbc:ID`, `cac:Signature/cac:SignatoryParty` | Signature ID + issuer RUC | `Invoice.issuer.ruc` | 006 |
| T-05 | Series and number | — | `cbc:ID` | `F001-123` (leading zeros not required) | `Invoice.number` | 005 |
| T-06 | Issue date | — | `cbc:IssueDate` | `yyyy-mm-dd` | `Invoice.issueDate` | 001 |
| T-07 | Issue time | — | `cbc:IssueTime` | `hh:mm:ss` | `Invoice.issueTime` | 001 |
| T-08 | Document type | `cat-01:01`, `cat-01:03` | `cbc:InvoiceTypeCode` | `listAgencyName="PE:SUNAT"`, `listName="Tipo de Documento"`, `listURI=…catalogo01` | `Invoice.documentType` | 001 |
| T-09 | Operation type | `cat-51:0101` | `cbc:InvoiceTypeCode/@listID` | `listID="0101"` | `Invoice.operationType` | 001 |
| T-10 | Amount in words | — (catalog 52, legend 1000) | `cbc:Note` | `languageLocaleID="1000"` | `Invoice.totals.amountInWords` | 001 |
| T-11 | Currency | `cat-02:PEN`, `cat-02:USD` | `cbc:DocumentCurrencyCode` | `listID="ISO 4217 Alpha"`, `listAgencyName="United Nations Economic Commission for Europe"` | `Invoice.currency` | 001 |

## 2. Issuer and buyer

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-12 | Issuer RUC | `cat-06:6` | `cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID` | `schemeID="6"`, `schemeAgencyName="PE:SUNAT"`, `schemeURI=…catalogo06` | `Invoice.issuer.ruc` | 004 |
| T-13 | Issuer legal name | — | `cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | — | `Invoice.issuer.legalName` | 001 |
| T-14 | Trade name | — | `cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name` | — | `Invoice.issuer.tradeName` | 001 |
| T-15 | Establishment code | — | `cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:AddressTypeCode` | `0000` = fiscal address | `Invoice.issuer.establishment` | 005 |
| T-16 | Buyer document type | `cat-06:6`, `cat-06:1`, `cat-06:-` | `cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID/@schemeID` | `schemeAgencyName="PE:SUNAT"` | `Invoice.customer.documentType` | 004 |
| T-17 | Buyer document number | — | `cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID` | RUC modulus 11 / 8-digit DNI | `Invoice.customer.documentNumber` | 004 |
| T-18 | Buyer name or legal name | — | `cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | — | `Invoice.customer.legalName` | 001 |
| T-19 | Buyer address | — | `cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cac:AddressLine/cbc:Line` | — | `Invoice.customer.address` | 001 |

## 3. Payment terms

Regulatory source: RS N.° 000193-2020/SUNAT, Annex IV (Annex 9-A, data items 170–173).

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-20 | Payment terms | — | `cac:PaymentTerms/cbc:PaymentMeansID` (with `cbc:ID` = `FormaPago`) | values `Contado` / `Credito` | `Invoice.paymentTerms.type` | 001 |
| T-21 | Net pending amount | — | `cac:PaymentTerms/cbc:Amount` | `currencyID` | `Invoice.paymentTerms.pendingAmount` | 001 |
| T-22 | Installments (amount and due date) | — | `cac:PaymentTerms/cbc:Amount`, `cac:PaymentTerms/cbc:PaymentDueDate` (with `cbc:PaymentMeansID` = `Cuota001`…) | `currencyID` | `Invoice.paymentTerms.installments[].amount`, `Invoice.paymentTerms.installments[].dueDate` | 001 |

## 4. Document totals and taxes

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-23 | Total tax amount | — | `cac:TaxTotal/cbc:TaxAmount` | `currencyID` | `Invoice.totals.taxTotal` | 003 |
| T-24 | Total taxed operations + IGV | `cat-05:1000` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount`, `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (TaxScheme 1000) | `cac:TaxScheme/cbc:ID`=1000, `cbc:Name`=IGV, `cbc:TaxTypeCode`=VAT | `Invoice.totals.taxedTotal`, `Invoice.totals.igvTotal` | 003 |
| T-25 | Total exempt | `cat-05:9997` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` (TaxScheme 9997) | `cbc:Name`=EXO, `cbc:TaxTypeCode`=VAT | `Invoice.totals.exemptTotal` | 003 |
| T-26 | Total unaffected | `cat-05:9998` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` (TaxScheme 9998) | `cbc:Name`=INA, `cbc:TaxTypeCode`=FRE | `Invoice.totals.unaffectedTotal` | 003 |
| T-27 | Total free of charge | `cat-05:9996` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` (TaxScheme 9996) | `cbc:Name`=GRA, `cbc:TaxTypeCode`=FRE | `Invoice.totals.freeTotal` | 003 |
| T-28 | Total ISC | `cat-05:2000` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (TaxScheme 2000) | `cbc:Name`=ISC, `cbc:TaxTypeCode`=EXC | `Invoice.totals.iscTotal` | 003 |
| T-29 | Total ICBPER | `cat-05:7152` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (TaxScheme 7152) | `cbc:Name`=ICBPER, `cbc:TaxTypeCode`=OTH | `Invoice.totals.icbperTotal` | 003 |
| T-30 | Total sale value | — | `cac:LegalMonetaryTotal/cbc:LineExtensionAmount` | `currencyID` | `Invoice.totals.saleValueTotal` | 003 |
| T-31 | Total sale price | — | `cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount` | `currencyID` | `Invoice.totals.salePriceTotal` | 003 |
| T-32 | Total discounts | — | `cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount` | `currencyID` | `Invoice.totals.discountTotal` | 003 |
| T-33 | Rounding | — | `cac:LegalMonetaryTotal/cbc:PayableRoundingAmount` | `currencyID` | `Invoice.totals.rounding` | 003 |
| T-34 | Total amount payable | — | `cac:LegalMonetaryTotal/cbc:PayableAmount` | `currencyID` | `Invoice.totals.payableAmount` | 003 |

## 5. Lines (`cac:InvoiceLine`)

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-40 | Item number | — | `cac:InvoiceLine/cbc:ID` | sequential from 1 | `Invoice.items[].lineNumber` | 001 |
| T-41 | Quantity and unit of measure | `cat-03:NIU`, `cat-03:ZZ` | `cac:InvoiceLine/cbc:InvoicedQuantity` | `unitCode`, `unitCodeListID="UN/ECE rec 20"` | `Invoice.items[].quantity`, `Invoice.items[].unitOfMeasure` | 001 |
| T-42 | Line sale value | — | `cac:InvoiceLine/cbc:LineExtensionAmount` | `currencyID` | `Invoice.items[].saleValue` | 003 |
| T-43 | Unit sale price | `cat-16:01` | `cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount` + `cbc:PriceTypeCode` | `listName="Tipo de Precio"`, `listURI=…catalogo16` | `Invoice.items[].unitPrice` | 003 |
| T-44 | Reference value (free of charge) | `cat-16:02` | `cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount` + `cbc:PriceTypeCode` | `PriceTypeCode=02` | `Invoice.items[].unitPrice` | 003 |
| T-45 | Unit value (before taxes) | — | `cac:InvoiceLine/cac:Price/cbc:PriceAmount` | `currencyID`; always 0 for free-of-charge items | `Invoice.items[].unitValue` | 003 |
| T-46 | Description | — | `cac:InvoiceLine/cac:Item/cbc:Description` | max. 500 | `Invoice.items[].description` | 001 |
| T-47 | Seller's product code | — | `cac:InvoiceLine/cac:Item/cac:SellersItemIdentification/cbc:ID` | — | `Invoice.items[].productCode` | 010 |
| T-48 | SUNAT product code | — (catalog 25, UNSPSC) | `cac:InvoiceLine/cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode` | `listID="UNSPSC"`, `listAgencyName="GS1 US"` | `Product.sunatProductCode` | 010 |
| T-49 | IGV affectation | `cat-07:10`, `cat-07:20`, `cat-07:30`, `cat-07:15` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode` | `listAgencyName="PE:SUNAT"`, `listURI=…catalogo07` | `Invoice.items[].igvAffectation` | 003 |
| T-50 | Line IGV base, rate and amount | `cat-05:1000` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount`, `cbc:TaxAmount`, `cac:TaxCategory/cbc:Percent` | `Percent`=18 | `Invoice.items[].igvBase`, `Invoice.items[].igv`, `Invoice.items[].igvRate` | 003 |
| **T-51** | **ISC calculation system** ★ | `cat-08:01`, `cat-08:02`, `cat-08:03` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` (TaxScheme 2000) | `cbc:TierRange` = catalog 08 code | `Invoice.items[].isc.system` | 003 |
| T-52 | Line ISC base, rate and amount | `cat-05:2000` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount`, `cbc:TaxAmount`, `cac:TaxCategory/cbc:Percent` (TaxScheme 2000) | `cbc:Name`=ISC, `cbc:TaxTypeCode`=EXC | `Invoice.items[].iscBase`, `Invoice.items[].iscAmount`, `Invoice.items[].isc.rate` (system 02 has no rate: `Percent` = iscAmount / iscBase, mandatory per SUNAT error 2992) | 003 |
| T-53 | Line ICBPER | `cat-05:7152` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:BaseUnitMeasure`, `cac:TaxCategory/cbc:PerUnitAmount`, `cbc:TaxAmount` (TaxScheme 7152) | `BaseUnitMeasure/@unitCode="NIU"` | `Invoice.items[].icbperBagCount`, `Invoice.items[].icbper` | 003 |
| T-54 | Line discount | — (catalog 53, code 00) | `cac:InvoiceLine/cac:AllowanceCharge/cbc:Amount` (`cbc:ChargeIndicator`=false) | `cbc:AllowanceChargeReasonCode="00"` | `Invoice.items[].discount` | 003 |
| T-55 | Line total taxes | — | `cac:InvoiceLine/cac:TaxTotal/cbc:TaxAmount` | `currencyID` | `Invoice.items[].totalTaxes` | 003 |

## 6. Credit notes (`CreditNote` root) and debit notes (`DebitNote` root)

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-60 | Note type | `cat-09:01`, `cat-09:07`, `cat-10:01` | `cac:DiscrepancyResponse/cbc:ResponseCode` | `listURI=…catalogo09` / `…catalogo10` | `Note.noteType` | 002 |
| T-61 | Reason | — | `cac:DiscrepancyResponse/cbc:Description` | — | `Note.reason` | 002 |
| T-62 | Affected document (series-number) | — | `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` | — | `Note.affectedDocument.number` | 002 |
| T-63 | Affected document type | `cat-01:01`, `cat-01:03` | `cac:BillingReference/cac:InvoiceDocumentReference/cbc:DocumentTypeCode` | `listURI=…catalogo01` | `Note.affectedDocument.documentType` | 002 |
| T-64 | Note quantity | `cat-03:NIU` | `cac:CreditNoteLine/cbc:CreditedQuantity` or `cac:DebitNoteLine/cbc:DebitedQuantity` | `unitCode` | `Note.items[].quantity` | 002 |
| T-65 | Note document type | `cat-01:07`, `cat-01:08` | `CreditNote` or `DebitNote` root | — | `Note.documentType` | 002 |
| T-66 | Total amount (debit note) | — | `cac:RequestedMonetaryTotal/cbc:PayableAmount` | Replaces `LegalMonetaryTotal` in `DebitNote` | `IssuedNote.totals.payableAmount` | 002 |

## 7. Response (CDR — `ApplicationResponse` root)

| ID | Data required by SUNAT | Catalog | UBL 2.1 XPath | Attributes (SUNAT customization) | DTO field | Spec |
|---|---|---|---|---|---|---|
| T-70 | Response code | — | `cac:DocumentResponse/cac:Response/cbc:ResponseCode` | 0 / 0100-1999 / 2000-3999 / ≥4000 | `Cdr.responseCode` | 007 |
| T-71 | Response description | — | `cac:DocumentResponse/cac:Response/cbc:Description` | — | `Cdr.description` | 007 |
| T-72 | Observations | — | `cbc:Note` | codes ≥ 4000 | `Cdr.notes` | 007 |

## 8. Cross-reference with the legacy system

| ID | Legacy field | Target in the new model | Does it reach a UBL element? | Rule |
|---|---|---|---|---|
| L-01 | `fecha` | `InventoryMovement.date` → K-10 | No (warehouse history, not an electronic document) | SPEC-009 M-02 |
| L-02 | `ingreso` | `InventoryMovement.quantity` (type INBOUND) → K-17 | No | SPEC-009 M-03 |
| L-03 | `salida` | `InventoryMovement.quantity` (type OUTBOUND) → K-18 | No | SPEC-009 M-03 |
| L-04 | `producto` | `Product.description` → K-15 and, in new sales, `cac:Item/cbc:Description` (T-46) | **Yes, indirectly** (the migrated product is used in new sales) | SPEC-009 M-04 |
| L-05 | `nro_documento` | `InventoryMovement.sourceDocument.number` → K-13 | **No**: it never becomes `cbc:ID` (T-05) | SPEC-009 M-05 · SPEC-005 R-07 |

## 9. Differences between generic UBL 2.1 (OASIS) and the SUNAT customization (Peru)

Complete Peruvian sample annotated with these rows: [20123456786-01-F001-123.xml](../specs/ref/20123456786-01-F001-123.xml).

| Element | Generic UBL (OASIS sample, EU) | SUNAT (Peru) |
|---|---|---|
| `cbc:CustomizationID` | Absent | Mandatory `2.0` |
| `cbc:InvoiceTypeCode` | `380` (UN/ECE 1001) | `01` / `03` (catalog 01) with `@listID` = operation type |
| Party identification | `cbc:EndpointID schemeID="GLN"` | `cac:PartyIdentification/cbc:ID schemeID="6"` (catalog 06) |
| Tax scheme | `TaxScheme/ID = VAT` (UN/ECE 5153) | `TaxScheme/ID = 1000` (catalog 05) + `Name` + `TaxTypeCode` |
| Tax category | `TaxCategory/ID = S, AA, E` (UN/ECE 5305) | `TaxExemptionReasonCode` (catalog 07) and `TierRange` for ISC (catalog 08) |
| Currency | `EUR` | `PEN` / `USD` |
| Tax-inclusive price | Not reported | `cac:PricingReference` mandatory (catalog 16) |
| Signature | Not included | `ext:UBLExtensions` + `cac:Signature` mandatory |
| Payment terms | `cac:PaymentMeans` (UN/ECE 4461 code) | `cac:PaymentTerms` with `ID="FormaPago"` (Contado / Credito / Cuota) |
| Legends | Free `cbc:Note` | `cbc:Note languageLocaleID` (catalog 52) |

## 10. Coverage

| Contract | Fields with a UBL counterpart | Fields without a counterpart (justified) |
|---|---|---|
| `Invoice` | See T-01 … T-55 | `id`, `status`, `links` (internal use); `sequenceNumber`, `series` (included in `number`, T-05); `cdr` (see T-70 … T-72); `customer.ubigeo`, `customer.email` (sending to the customer); `items[].isc.fixedAmount`, `items[].isc.unitConversionFactor`, `items[].isc.retailPrice` (calculation parameters: reflected in the T-52 amount); `items[].referenceUnitValue` (input, returned as `unitPrice`, T-44); `exchangeRate` (not in the XML; feeds V-27); `totals.exportTotal` (phase 2, tax 9995) |
| `Note` | T-60 … T-66 | `series`, `issueDate` and `currency` follow the same rows as in `Invoice` (T-05, T-06, T-11) |
| `Cdr` | T-70 … T-72 | `result` (derived), `channel`, `ticket`, `receivedAt` |

## 11. Format 14.1 — Sales and income record (PLE code 140100)

Regulatory source: Annex 2 of RS 286-2009/SUNAT, in the layout of RS 361-2015/SUNAT and RS 108-2020/SUNAT
(35 fields, with ICBPER in field 23). Fields 36–70 are free-use and are not generated. The row number
equals the PLE field number. The sample record is [LE2012345678620261000140100001111.TXT](../specs/ref/ple/LE2012345678620261000140100001111.TXT).

| ID | PLE field | PLE table | Origin (UBL / domain) | DTO field | Rule |
|---|---|---|---|---|---|
| V-01 | Period | — | Issue date → `YYYYMM00` | `SalesRecordLine.period` | SPEC-013 R-01 |
| V-02 | Unique operation code (CUO) | — | Derived: `{type}-{series}-{number}` | `SalesRecordLine.cuo` | SPEC-013 R-02 |
| V-03 | Entry number (A/M/C + sequence) | — | Book sequence for the period | `SalesRecordLine.entryNumber` | SPEC-013 R-02 |
| V-04 | Document issue date | — | `cbc:IssueDate` (T-06) | `SalesRecordLine.issueDate` | SPEC-013 R-03 |
| V-05 | Due or payment date | — | Mandatory only for table 10 code 14; not used by ABC | `SalesRecordLine.dueDate` | SPEC-013 R-03 |
| V-06 | Document type | `table-10:01`, `table-10:03`, `table-10:07`, `table-10:08` | `cbc:InvoiceTypeCode` (T-08) or UBL root (T-65) | `SalesRecordLine.documentType` | SPEC-013 R-04 |
| V-07 | Series | — | First part of `cbc:ID` (T-05) | `SalesRecordLine.series` | SPEC-005 R-01 |
| V-08 | Number | — | Second part of `cbc:ID` (T-05) | `SalesRecordLine.number` | SPEC-005 R-03 |
| V-09 | Final number of a consolidated range | — | Sales receipts consolidated per day | `SalesRecordLine.finalNumber` | SPEC-013 R-05 |
| V-10 | Customer document type | `table-02:6`, `table-02:1` | `…/cbc:ID/@schemeID` (T-16) through the catalog 06 → table 2 mapping | `SalesRecordLine.customerDocumentType` | SPEC-013 R-05 |
| V-11 | Customer document number | — | `cac:AccountingCustomerParty/…/cbc:ID` (T-17) | `SalesRecordLine.customerDocumentNumber` | SPEC-013 R-05 |
| V-12 | Customer name or legal name | — | `…/cbc:RegistrationName` (T-18) | `SalesRecordLine.customerName` | SPEC-013 R-05 |
| V-13 | Export invoiced value | — | TaxScheme 9995 (phase 2); `0.00` in phase 1 | `SalesRecordLine.exportValue` | SPEC-013 R-06 |
| V-14 | Taxed base (excludes ISC) | — | `cac:TaxSubtotal/cbc:TaxableAmount`, TaxScheme 1000 (T-24); `totals.taxedTotal` | `SalesRecordLine.taxableBase` | SPEC-013 R-06 |
| V-15 | Discount on the taxed base | — | Credit notes type 04 / 05 (T-60) | `SalesRecordLine.taxableBaseDiscount` | SPEC-013 R-07 |
| V-16 | IGV and/or IPM | — | `cac:TaxSubtotal/cbc:TaxAmount`, TaxScheme 1000 (T-24); `totals.igvTotal` | `SalesRecordLine.igv` | SPEC-013 R-06 |
| V-17 | Discount on the IGV | — | Credit notes type 04 / 05 (T-60) | `SalesRecordLine.igvDiscount` | SPEC-013 R-07 |
| V-18 | Total exempt amount | — | TaxScheme 9997 (T-25); `totals.exemptTotal` | `SalesRecordLine.exemptAmount` | SPEC-013 R-06 |
| V-19 | Total unaffected amount | — | TaxScheme 9998 (T-26); `totals.unaffectedTotal` | `SalesRecordLine.unaffectedAmount` | SPEC-013 R-06 |
| V-20 | ISC | — | TaxScheme 2000 (T-28); `totals.iscTotal` | `SalesRecordLine.isc` | SPEC-013 R-06 |
| V-21 | IVAP taxed base | — | Not applicable to ABC (table 10 code 49); empty or `0.00` | (not modelled) | SPEC-013 R-06 |
| V-22 | IVAP | — | Not applicable to ABC; empty or `0.00` | (not modelled) | SPEC-013 R-06 |
| V-23 | ICBPER | — | TaxScheme 7152 (T-29); `totals.icbperTotal` | `SalesRecordLine.icbper` | SPEC-013 R-06 |
| V-24 | Other charges outside the base | — | `cac:LegalMonetaryTotal/cbc:ChargeTotalAmount` | `SalesRecordLine.otherCharges` | SPEC-013 R-06 |
| V-25 | Document total | — | `cac:LegalMonetaryTotal/cbc:PayableAmount` (T-34) | `SalesRecordLine.total` | SPEC-013 R-06 |
| V-26 | Currency | — | `cbc:DocumentCurrencyCode` (T-11) | `SalesRecordLine.currency` | SPEC-013 R-08 |
| V-27 | Exchange rate | — | `Invoice.exchangeRate`; `1.000` in PEN | `SalesRecordLine.exchangeRate` | SPEC-013 R-08 |
| V-28 | Modified document: issue date | — | Issue date of the affected document (T-62) | `SalesRecordLine.modifiedDocument.issueDate` | SPEC-013 R-07 |
| V-29 | Modified document: type | `table-10:01`, `table-10:03` | `…/cbc:DocumentTypeCode` (T-63) | `SalesRecordLine.modifiedDocument.documentType` | SPEC-013 R-07 |
| V-30 | Modified document: series | — | First part of `…/cbc:ID` (T-62) | `SalesRecordLine.modifiedDocument.series` | SPEC-013 R-07 |
| V-31 | Modified document: number | — | Second part of `…/cbc:ID` (T-62) | `SalesRecordLine.modifiedDocument.number` | SPEC-013 R-07 |
| V-32 | Collaboration contract ID | — | Not applicable to ABC; empty | (not modelled) | SPEC-013 R-06 |
| V-33 | Exchange rate inconsistency flag | — | Calculated at export; empty when consistent | (calculated at export) | SPEC-013 R-08 |
| V-34 | Paid through a payment medium | — | Payment data recorded for the document | `SalesRecordLine.paidWithPaymentMedium` | SPEC-013 R-09 |
| V-35 | Entry status | — | Derived from `Invoice.status` and the period | `SalesRecordLine.status` | SPEC-013 R-10 |

## 12. Format 12.1 — Permanent inventory in physical units (PLE code 120100)

Regulatory source: Annex 2 of RS 286-2009/SUNAT as amended (structure published with RS 042-2018/SUNAT) and
the printed format of RS 234-2006/SUNAT, which adds the final balance column. Fields 20–38 are free-use and are
not generated. The row number equals the PLE field number. The sample record is
[LE2012345678620261000120100001111.TXT](../specs/ref/ple/LE2012345678620261000120100001111.TXT).

| ID | PLE field | PLE table | Origin (domain) | DTO field | Legacy origin | Rule |
|---|---|---|---|---|---|---|
| K-01 | Period | — | `InventoryMovement.date` → `YYYYMM00` | `InventoryRecordLine.period` | `fecha` | SPEC-013 R-01 |
| K-02 | Unique operation code (CUO) | — | Sale: same CUO as V-02. Other movements: derived from the movement | `InventoryRecordLine.cuo` | `sourceRow` (`LEG-{row}`) | SPEC-013 R-02 |
| K-03 | Entry number (A/M/C + sequence) | — | Book sequence; `A` for the opening balance | `InventoryRecordLine.entryNumber` | — | SPEC-013 R-02 |
| K-04 | Annex establishment code | — | `InventoryMovement.establishmentCode` | `InventoryRecordLine.establishmentCode` | Default `0000` (M-10) | SPEC-013 R-11 |
| K-05 | Catalog of the own code | — | Constant for the own product catalog | (constant) | — | SPEC-013 R-12 |
| K-06 | Existence type | `table-05:01` | `InventoryMovement.existenceType` | `InventoryRecordLine.existenceType` | Default `01` (M-10) | SPEC-013 R-11 |
| K-07 | Own product code | — | `InventoryMovement.productCode` | `InventoryRecordLine.productCode` | `producto` (M-04) | SPEC-013 R-11 |
| K-08 | Catalog of the classification code | — | Constant for UNSPSC | (constant) | — | SPEC-013 R-12 |
| K-09 | Classification code (16 digits) | — | `Product.sunatProductCode` + `00000000` (T-48) | `InventoryRecordLine.sunatProductCode` | Admin review (M-04) | SPEC-013 R-12 |
| K-10 | Document date | — | `InventoryMovement.date` | `InventoryRecordLine.documentDate` | `fecha` (M-02) | SPEC-013 R-03 |
| K-11 | Document type | `table-10:00`, `table-10:01`, `table-10:03`, `table-10:07` | `InventoryMovement.sourceDocument.documentType` | `InventoryRecordLine.documentType` | `00` (M-05) | SPEC-013 R-13 |
| K-12 | Document series | — | `InventoryMovement.sourceDocument.series` | `InventoryRecordLine.series` | `0` (M-05) | SPEC-013 R-13 |
| K-13 | Document number | — | `InventoryMovement.sourceDocument.number` | `InventoryRecordLine.number` | `nro_documento` (M-05) | SPEC-013 R-13 |
| K-14 | Operation type | `table-12:01`, `table-12:02`, `table-12:05`, `table-12:16`, `table-12:99` | `InventoryMovement.operationType` | `InventoryRecordLine.operationType` | `99` (M-11) | SPEC-013 R-13 |
| K-15 | Existence description | — | `Product.description` (max. 80) | `InventoryRecordLine.description` | `producto` (M-04) | SPEC-013 R-11 |
| K-16 | Unit of measure | `table-06:07`, `table-06:01`, `table-06:08`, `table-06:12` | `InventoryMovement.unitOfMeasure` through the UnitMappingCatalog | `InventoryRecordLine.unitOfMeasure` | Default `NIU` → `07` (M-04) | SPEC-013 R-14 |
| K-17 | Entries (the first record is the opening balance) | — | `InventoryMovement.quantity`, type INBOUND × unit factor | `InventoryRecordLine.entries` | `ingreso` (M-03) | SPEC-013 R-15 |
| K-18 | Exits (negative) | — | `InventoryMovement.quantity`, type OUTBOUND × unit factor × −1 | `InventoryRecordLine.exits` | `salida` (M-03) | SPEC-013 R-15 |
| K-19 | Operation status | — | `1`, `8` or `9` according to the period | `InventoryRecordLine.status` | — | SPEC-013 R-10 |
