# SPEC-006: UBL 2.1 XML generation and digital signature

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** ADR-003, ADR-005 · [Traceability matrix](../../docs/05-traceability-matrix.md)

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
| R-09 | ISO-8859-1 encoding, as SUNAT requires; characters outside Latin-1 are written as numeric references (`&#8364;`); special characters escaped. |
| R-10 | The signed XML and the CDR are kept for the legal retention period. |

## Acceptance criteria
- **AC-1:** Given the document in [invoice-response.json](../schemas/examples/invoice-response.json), when I generate the XML, then it is equivalent to [20123456786-01-F001-123.xml](../ref/20123456786-01-F001-123.xml) and validates against `UBL-Invoice-2.1.xsd` (`python -m pytest`).
- **AC-2:** Given a signed XML, when I alter an amount, then signature verification fails.
- **AC-3:** Given an expired certificate, then signing is rejected with a configuration error and the document does not move past `DRAFT`.

## Implementation
The invoice (01 and 03) is implemented in [invoice_generator.py](../../src/abc_invoicing/adapters/ubl/invoice_generator.py) with tests in [test_invoice_generation.py](../../tests/test_invoice_generation.py). R-05 (signing) is implemented in [xml_signer.py](../../src/abc_invoicing/adapters/signature/xml_signer.py) (RSA-SHA256, inclusive C14N 1.0) with tests in [test_xml_signature.py](../../tests/test_xml_signature.py), covering AC-2 and AC-3. R-08: the SUNAT file name is implemented (`Invoice.file_name`, CLI option `-d`); the ZIP file and the `CreditNote` and `DebitNote` roots are not implemented yet. Phase 2 codes (operation types other than 0101, affectations 17 and 40) are rejected by the domain (SPEC-011 R-03).

## References
- SUNAT sample XML and XSD validation: [specs/ref/](../ref/README.md)
