# SPEC-006: Generación de XML UBL 2.1 y firma digital

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** ADR-001, ADR-003 · [Matriz de trazabilidad](../../docs/05-matriz-trazabilidad.md)

## Resumen
Traducir el agregado `Comprobante` a XML conforme a `UBL-Invoice-2.1.xsd`,
`UBL-CreditNote-2.1.xsd` o `UBL-DebitNote-2.1.xsd`, con la personalización SUNAT, y firmarlo
con XMLDSig.

## Reglas
| ID | Regla |
|---|---|
| R-01 | Raíz según catálogo 01: 01/03 → `Invoice`; 07 → `CreditNote`; 08 → `DebitNote`. |
| R-02 | `cbc:UBLVersionID = 2.1`, `cbc:CustomizationID = 2.0`. |
| R-03 | Todos los códigos llevan sus atributos de lista (`listAgencyName="PE:SUNAT"`, `listURI` del catálogo), según la matriz. |
| R-04 | El XML debe validar contra el XSD oficial **antes** de firmar; si no valida, no se firma ni se envía. |
| R-05 | Firma XMLDSig *enveloped* dentro de `ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent`; algoritmo RSA-SHA256 (o el que exija la norma vigente); referencia URI="". |
| R-06 | `cac:Signature` con ID de firma, RUC y razón social del emisor. |
| R-07 | El `DigestValue` se guarda como `hashCpe` y se imprime en la representación impresa. |
| R-08 | Nombre del archivo: `{RUC}-{TIPO}-{SERIE}-{CORRELATIVO}.xml`, comprimido en `.zip` de igual nombre. |
| R-09 | Codificación UTF-8 (ISO-8859-1 admitido por SUNAT); caracteres especiales escapados. |
| R-10 | Se conservan XML firmado y CDR por el plazo legal de conservación. |

## Criterios de aceptación
- **AC-1:** Dado el comprobante de [factura-response.json](../schemas/examples/factura-response.json), cuando genero el XML, entonces valida contra `UBL-Invoice-2.1.xsd`.
- **AC-2:** Dado un XML firmado, cuando altero un monto, entonces la verificación de firma falla.
- **AC-3:** Dado un certificado vencido, entonces la firma se rechaza con error de configuración y el comprobante no avanza de `BORRADOR`.

## Referencias
- XSD y ejemplo OASIS: [specs/ref/](../ref/README.md)
