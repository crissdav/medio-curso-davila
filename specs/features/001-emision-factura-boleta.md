# SPEC-001: Emisión de Factura y Boleta electrónica

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-01, UC-02, UC-14, UC-17 · SPEC-003, 004, 005, 006, 007 · ADR-002

## Resumen
Permitir emitir Facturas (01) y Boletas (03) electrónicas válidas ante SUNAT a partir de una
venta, con cálculo automático de tributos y numeración controlada.

## Motivación
El sistema actual "no genera XMLs" ni emite comprobantes legales (RS 097-2012/SUNAT).

## Alcance
- **Incluye:** venta interna (0101), moneda PEN/USD, forma de pago Contado o Crédito con cuotas,
  representación impresa (A4 y ticket), envío al cliente por correo.
- **No incluye:** exportación, detracción, anticipos, percepción (fase 2).

## Reglas de negocio
| ID | Regla |
|---|---|
| R-01 | Factura: serie `F###` y cliente con RUC (catálogo 06 = 6) válido según SPEC-004. |
| R-02 | Boleta: serie `B###`; cliente con DNI u otro documento del catálogo 06. |
| R-03 | La fecha de emisión no puede ser futura ni anterior al plazo máximo de envío vigente. |
| R-04 | Boleta con importe total mayor al umbral vigente (S/ 700) exige identificar al cliente (no se admite `-`). |
| R-05 | Moneda distinta de PEN exige `tipoCambio`. |
| R-06 | Forma de pago Crédito exige `montoPendiente` y al menos una cuota; Σ cuotas = montoPendiente; fechas de cuota > fecha de emisión. |
| R-07 | Los importes se calculan siempre en el servidor (SPEC-003); se ignoran totales enviados por el cliente. |
| R-08 | La representación impresa incluye código QR con: RUC, tipo, serie, número, IGV, total, fecha, tipo y número de documento del cliente y hash. |

## Criterios de aceptación
- **AC-1:** Dado un cliente con RUC válido y activo, cuando emito una factura con serie F001, entonces obtengo 201 con número `F001-<correlativo>` y estado `ACEPTADO` u `OBSERVADO`.
- **AC-2:** Dada una factura con cliente DNI, cuando la emito, entonces obtengo 400 `RUC_INVALIDO`/validación de esquema.
- **AC-3:** Dada una boleta de S/ 750 con cliente `-`, cuando la emito, entonces obtengo 400 `CLIENTE_REQUERIDO_BOLETA`.
- **AC-4:** Dada una venta en USD sin tipo de cambio, cuando la emito, entonces obtengo 400.
- **AC-5:** Dada una factura a crédito con cuotas que no suman el pendiente, cuando la emito, entonces obtengo 400.
- **AC-6:** Dado el ejemplo [factura-request.json](../schemas/examples/factura-request.json), cuando lo emito, entonces los totales coinciden con [factura-response.json](../schemas/examples/factura-response.json).
- **AC-7:** Dada la misma `Idempotency-Key` enviada dos veces, entonces se devuelve el mismo comprobante y el correlativo avanza una sola vez.

## Contratos
- `POST /comprobantes` · [comprobante.schema.json](../schemas/comprobante.schema.json)

## Casos borde
- Venta con 500 ítems (máximo).
- Cliente con razón social con caracteres especiales (`&`, `Ñ`) → escapado XML correcto.

## Preguntas abiertas
- ¿Se bloquea la emisión a clientes NO HABIDOS o solo se advierte? (ver SPEC-004).
