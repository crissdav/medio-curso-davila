# SPEC-006: UBL 2.1 XML generation and digital signature

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** ADR-001, ADR-003 · [Traceability matrix](../../docs/05-traceability-matrix.md)

## Summary
Translate the `Invoice` aggregate into XML compliant with `UBL-Invoice-2.1.xsd`,
`UBL-CreditNote-2.1.xsd` or `UBL-DebitNote-2.1.xsd`, with the SUNAT customization, and sign it
with XMLDSig.

## Rules
| ID | Rule |
|---|---|
| R-01 | Root according to catalog 01: 01/03 → `Invoice`; 07 → `CreditNote`; 08 → `DebitNote`. |
| R-02 | `cbc:UBLVersionID = 2.1`, `cbc:CustomizationID = 2.0`. |
| R-03 | Every code carries its list attributes (`listAgencyName="PE:SUNAT"`, the catalog `listURI`), according to the matrix. |
| R-04 | The XML must validate against the official XSD **before** signing; if it does not validate, it is neither signed nor submitted. |
| R-05 | *Enveloped* XMLDSig signature inside `ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent`; RSA-SHA256 algorithm (or whatever the current regulation requires); reference URI="". |
| R-06 | `cac:Signature` with the signature ID, issuer RUC and legal name. |
| R-07 | The `DigestValue` is stored as `documentHash` and printed on the printed representation. |
| R-08 | File name: `{RUC}-{TYPE}-{SERIES}-{NUMBER}.xml`, compressed into a `.zip` with the same name. |
| R-09 | UTF-8 encoding (ISO-8859-1 accepted by SUNAT); special characters escaped. |
| R-10 | The signed XML and the CDR are kept for the legal retention period. |

## Acceptance criteria
- **AC-1:** Given the document in [invoice-response.json](../schemas/examples/invoice-response.json), when I generate the XML, then it is equivalent to [20123456786-01-F001-123.xml](../ref/20123456786-01-F001-123.xml) and validates against `UBL-Invoice-2.1.xsd` (`npm run check:xsd`).
- **AC-2:** Given a signed XML, when I alter an amount, then signature verification fails.
- **AC-3:** Given an expired certificate, then signing is rejected with a configuration error and the document does not move past `DRAFT`.

## References
- SUNAT sample XML and XSD validation: [specs/ref/](../ref/README.md)
