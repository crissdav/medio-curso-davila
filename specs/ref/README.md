# Referencias UBL 2.1 — Perú (personalización SUNAT)

Todos los contratos de este repositorio siguen **UBL 2.1 con la personalización de SUNAT (Perú)**:
`CustomizationID 2.0`, códigos `PE:SUNAT` y catálogos del Anexo 8.

| Archivo | Descripción |
|---|---|
| [20123456786-01-F001-123.xml](20123456786-01-F001-123.xml) | Factura del caso ABC (abarrotes con ISC catálogo 08 e ICBPER). Equivale a [factura-response.json](../schemas/examples/factura-response.json); cada elemento está anotado con su fila `T-nn` de la [matriz](../../docs/05-matriz-trazabilidad.md). |
| [sunat-factura-minima-ejemplo.xml](sunat-factura-minima-ejemplo.xml) | Factura SUNAT mínima de terceros, copia de [giansalex (autor de Greenter)](https://gist.github.com/giansalex/6cab789ed1d9ee838216c3847862a030). Es de 2020: no incluye `cac:PaymentTerms` (forma de pago), exigido después. |

Ambos XML están **sin firma**: la firma XMLDSig se inserta en `ext:ExtensionContent` al firmar (SPEC-006).

## Validación contra el XSD oficial

```bash
npm run check:xsd   # java scripts/ValidarXsd.java — descarga los XSD de OASIS en .cache/ la primera vez
```

Valida cada XML contra `UBL-Invoice-2.1.xsd` (o `CreditNote` / `DebitNote` según la raíz). El XSD
verifica la estructura y el orden de los elementos; las reglas de negocio de SUNAT (códigos 2xxx–4xxx)
se validan en el dominio (SPEC-003, SPEC-004, SPEC-005).

## Fuentes oficiales

| Recurso | Ubicación |
|---|---|
| XSD UBL 2.1 (Invoice, CreditNote, DebitNote, ApplicationResponse) | <https://docs.oasis-open.org/ubl/os-UBL-2.1/> |
| Guía de elaboración XML UBL 2.1 — Factura (SUNAT) | <https://cpe.sunat.gob.pe/> |
| Anexo 8 — Catálogos SUNAT | <https://cpe.sunat.gob.pe/> |
