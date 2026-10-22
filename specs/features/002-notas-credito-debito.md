# SPEC-002: Notas de Crédito y Débito electrónicas

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-03, UC-04 · SPEC-001, 003, 006 · Catálogos 09 y 10

## Resumen
Emitir Notas de Crédito (07, UBL `CreditNote`) y de Débito (08, UBL `DebitNote`) que modifican
un comprobante ya aceptado.

## Motivación
Un comprobante aceptado es inmutable (INV-06). Descuentos posteriores, devoluciones, anulaciones,
intereses o penalidades solo pueden reflejarse mediante notas.

## Reglas de negocio
| ID | Regla |
|---|---|
| R-01 | El documento afectado debe existir, ser del mismo emisor y estar `ACEPTADO` u `OBSERVADO`. |
| R-02 | La serie de la nota tiene el mismo prefijo que el afectado: nota de factura `F###`, nota de boleta `B###`. |
| R-03 | `tipoNota` debe pertenecer al catálogo 09 (crédito) o 10 (débito). |
| R-04 | Nota de crédito: Σ notas de crédito sobre un comprobante ≤ importe total del afectado. |
| R-05 | Tipo 01 (anulación) o 06 (devolución total) ⇒ la nota replica todas las líneas y el afectado pasa a `ANULADO`. |
| R-06 | La moneda de la nota = moneda del afectado. |
| R-07 | Devolución (06, 07) genera movimiento de `INGRESO` en inventario (SPEC-010). |

## Criterios de aceptación
- **AC-1:** Dada la factura `F001-00000123` aceptada, cuando emito una NC tipo 07 por 2 gaseosas, entonces se emite con serie F001 y se registra un ingreso de 2 unidades.
- **AC-2:** Dada una boleta, cuando emito una nota con serie `F001`, entonces obtengo 400 `SERIE_INCOMPATIBLE`.
- **AC-3:** Dada una factura de S/ 100 con NC previa de S/ 80, cuando emito otra NC de S/ 30, entonces obtengo 400.
- **AC-4:** Dada una ND con `tipoNota` = 05, entonces obtengo 400 (no existe en catálogo 10).

## Contratos
- `POST /notas` · [nota.schema.json](../schemas/nota.schema.json) · ejemplo [nota-credito-request.json](../schemas/examples/nota-credito-request.json)

## Preguntas abiertas
- Plazo máximo para emitir NC sobre un comprobante (verificar normativa vigente).
