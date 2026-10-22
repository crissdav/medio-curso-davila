# SPEC-010: Inventario integrado a ventas

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-10, UC-16 · SPEC-002, 008, 009

## Resumen
Mantener la funcionalidad de almacén actual (ingresos y salidas) y conectarla con la facturación:
cada venta aceptada descuenta stock y cada devolución o baja lo repone.

## Reglas
| ID | Regla |
|---|---|
| R-01 | El evento `ComprobanteAceptado` (u `OBSERVADO`) genera un movimiento `SALIDA` por línea de bien (no servicios `ZZ`), con `documentoReferencia.tipo = COMPROBANTE`. |
| R-02 | Nota de crédito tipo 06/07 y baja confirmada generan movimiento `INGRESO`. |
| R-03 | Un comprobante `RECHAZADO` no mueve stock. |
| R-04 | Los movimientos son inmutables; las correcciones se hacen con `AJUSTE` con motivo. |
| R-05 | El kardex muestra movimientos `NUEVO` y `LEGADO` en una sola línea de tiempo. |
| R-06 | El producto define su configuración tributaria (afectación IGV, ISC catálogo 08, ICBPER) que se propone por defecto en la venta. |
| R-07 | Venta con stock insuficiente: advertencia configurable (no bloquea la emisión fiscal). |

## Criterios de aceptación
- **AC-1:** Dada la factura de referencia aceptada, entonces el stock de `CER-620` baja en 12.
- **AC-2:** Dada la NC de [nota-credito-request.json](../schemas/examples/nota-credito-request.json), entonces el stock de `GAS-3L` sube en 2.
- **AC-3:** Dado un producto migrado con `requiereRevision = true`, cuando intento venderlo, entonces se pide confirmar su configuración tributaria.

## Contratos
- `GET/POST /productos`, `GET/POST /inventario/movimientos` · [producto.schema.json](../schemas/producto.schema.json) · [movimiento-inventario.schema.json](../schemas/movimiento-inventario.schema.json)
