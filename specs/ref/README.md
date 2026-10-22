# Referencias UBL 2.1

| Recurso | Ubicación |
|---|---|
| Ejemplo oficial OASIS de factura UBL 2.1 | [UBL-Invoice-2.1-Example.xml](UBL-Invoice-2.1-Example.xml) — copia de [Tradeshift/tradeshift-ubl-xsd](https://github.com/Tradeshift/tradeshift-ubl-xsd/blob/master/src/test/resources/org/oasis-open/ubl/examples/UBL-Invoice-2.1-Example.xml) |
| XSD de factura | `xsd/maindoc/UBL-Invoice-2.1.xsd` del paquete oficial OASIS UBL 2.1: <https://docs.oasis-open.org/ubl/os-UBL-2.1/> |
| XSD de nota de crédito / débito | `xsd/maindoc/UBL-CreditNote-2.1.xsd`, `xsd/maindoc/UBL-DebitNote-2.1.xsd` (mismo paquete) |
| XSD de CDR | `xsd/maindoc/UBL-ApplicationResponse-2.1.xsd` |
| Personalización peruana | Guías de elaboración de documentos XML UBL 2.1 y Anexo 8 (catálogos) publicados por SUNAT en <https://cpe.sunat.gob.pe/> |

El ejemplo es UBL genérico (UE); sus diferencias con la personalización SUNAT están en la
sección 9 de la [matriz de trazabilidad](../../docs/05-matriz-trazabilidad.md). Los XSD no se
versionan aquí: se descargan en el build para generar JAXB y validar el XML (SPEC-006 R-04).
