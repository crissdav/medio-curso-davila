# UBL 2.1 references — Peru (SUNAT customization)

All contracts in this repository follow **UBL 2.1 with the SUNAT (Peru) customization**:
`CustomizationID 2.0`, `PE:SUNAT` codes and the Annex 8 catalogs.

| File | Description |
|---|---|
| [20123456786-01-F001-123.xml](20123456786-01-F001-123.xml) | Invoice of the ABC case (groceries with catalog 08 ISC and ICBPER). Equivalent to [invoice-response.json](../schemas/examples/invoice-response.json); every element is annotated with its `T-nn` row of the [matrix](../../docs/05-traceability-matrix.md). |
| [sunat-factura-minima-ejemplo.xml](sunat-factura-minima-ejemplo.xml) | Minimal third-party SUNAT invoice, copied unchanged from [giansalex (author of Greenter)](https://gist.github.com/giansalex/6cab789ed1d9ee838216c3847862a030). It dates from 2020: it does not include `cac:PaymentTerms` (payment terms), required later. |

Both XML files are **unsigned**: the XMLDSig signature is inserted into `ext:ExtensionContent` when signing (SPEC-006).

## Two-layer validation

> OASIS UBL 2.1 provides the **structure**; the SUNAT customization defines the **values** for Peru.
> That is why every XML is validated against both.

| Layer | Command | What it checks |
|---|---|---|
| **Structure (OASIS)** | `npm run check:xsd` | The XML complies with `UBL-Invoice-2.1.xsd` (or `CreditNote` / `DebitNote`): elements, order and types. Downloads the XSDs into `.cache/` the first time (requires JDK 11+). |
| **Content (SUNAT)** | `npm run check:sunat` | Codes present in the catalogs of [specs/catalogs/](../catalogs/) (01, 02, 03, 05, 06, 07, 08, 16, 51); `CustomizationID 2.0`; F/B series according to the type; RUC modulus 11; invoice → customer with RUC; ISC with `TierRange`; line, tax and total arithmetic; and a **field-by-field cross-check with the equivalent JSON**. Every error cites its `T-nn` matrix row. |

`npm run check:ubl` runs both layers. Current result:

- `20123456786-01-F001-123.xml`: complies with the XSD and passes the 164 SUNAT checks.
- `sunat-factura-minima-ejemplo.xml` (third party, informational only): complies with the XSD, but
  uses a fictitious RUC that fails modulus 11 and does not report the payment terms.

## Official sources

| Resource | Location |
|---|---|
| UBL 2.1 XSDs (Invoice, CreditNote, DebitNote, ApplicationResponse) | <https://docs.oasis-open.org/ubl/os-UBL-2.1/> |
| UBL 2.1 XML guide — Invoice (SUNAT) | <https://cpe.sunat.gob.pe/> |
| Annex 8 — SUNAT catalogs | <https://cpe.sunat.gob.pe/> |
