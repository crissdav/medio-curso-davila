# Referencias UBL 2.1 — Perú (personalización SUNAT)

Todos los contratos de este repositorio siguen **UBL 2.1 con la personalización de SUNAT (Perú)**:
`CustomizationID 2.0`, códigos `PE:SUNAT` y catálogos del Anexo 8.

| Archivo | Descripción |
|---|---|
| [20123456786-01-F001-123.xml](20123456786-01-F001-123.xml) | Factura del caso ABC (abarrotes con ISC catálogo 08 e ICBPER). Equivale a [factura-response.json](../schemas/examples/factura-response.json); cada elemento está anotado con su fila `T-nn` de la [matriz](../../docs/05-matriz-trazabilidad.md). |
| [sunat-factura-minima-ejemplo.xml](sunat-factura-minima-ejemplo.xml) | Factura SUNAT mínima de terceros, copia de [giansalex (autor de Greenter)](https://gist.github.com/giansalex/6cab789ed1d9ee838216c3847862a030). Es de 2020: no incluye `cac:PaymentTerms` (forma de pago), exigido después. |

Ambos XML están **sin firma**: la firma XMLDSig se inserta en `ext:ExtensionContent` al firmar (SPEC-006).

## Validación en dos capas

> UBL 2.1 de OASIS da la **estructura**; la personalización SUNAT define los **valores** para Perú.
> Por eso cada XML se valida contra ambas.

| Capa | Comando | Qué verifica |
|---|---|---|
| **Estructura (OASIS)** | `npm run check:xsd` | El XML cumple `UBL-Invoice-2.1.xsd` (o `CreditNote` / `DebitNote`): elementos, orden y tipos. Descarga los XSD en `.cache/` la primera vez (requiere JDK 11+). |
| **Contenido (SUNAT)** | `npm run check:sunat` | Códigos en los catálogos de [specs/catalogos/](../catalogos/) (01, 02, 03, 05, 06, 07, 08, 16, 51); `CustomizationID 2.0`; serie F/B según el tipo; RUC módulo 11; factura → cliente con RUC; ISC con `TierRange`; aritmética de líneas, impuestos y totales; y **cruce campo por campo con el JSON equivalente**. Cada error cita su fila `T-nn` de la matriz. |

`npm run check:ubl` ejecuta ambas capas. Resultado actual:

- `20123456786-01-F001-123.xml`: cumple el XSD y las 164 verificaciones SUNAT.
- `sunat-factura-minima-ejemplo.xml` (terceros, solo informativo): cumple el XSD, pero usa un RUC
  ficticio que no pasa módulo 11 y no informa la forma de pago.

## Fuentes oficiales

| Recurso | Ubicación |
|---|---|
| XSD UBL 2.1 (Invoice, CreditNote, DebitNote, ApplicationResponse) | <https://docs.oasis-open.org/ubl/os-UBL-2.1/> |
| Guía de elaboración XML UBL 2.1 — Factura (SUNAT) | <https://cpe.sunat.gob.pe/> |
| Anexo 8 — Catálogos SUNAT | <https://cpe.sunat.gob.pe/> |
