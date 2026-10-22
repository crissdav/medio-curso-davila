# SPEC-005: Series y correlativos

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-11 · INV-05 · SPEC-001, 002

## Resumen
Administrar series por tipo de comprobante y establecimiento, y asignar correlativos únicos,
consecutivos y no reutilizables.

## Reglas de negocio
| ID | Regla |
|---|---|
| R-01 | Serie = 4 caracteres alfanuméricos: `F` + 3 para facturas y sus notas; `B` + 3 para boletas y sus notas. |
| R-02 | Solo se emite con series registradas y activas para ese tipo y establecimiento → si no, `SERIE_NO_AUTORIZADA`. |
| R-03 | Correlativo de 1 a 99 999 999, único por (RUC, tipo, serie). Al llegar al máximo se exige una serie nueva. |
| R-04 | Asignación atómica (bloqueo pesimista por fila de serie) dentro de la transacción de emisión. |
| R-05 | Un correlativo asignado **nunca** se reutiliza, ni si SUNAT rechaza el comprobante. |
| R-06 | `Idempotency-Key` repetida devuelve el comprobante ya creado sin asignar un nuevo correlativo. |
| R-07 | Los correlativos legados (`nro_documento`) **no** se cargan como correlativos SUNAT (SPEC-009). |

## Criterios de aceptación
- **AC-1:** Dadas 50 emisiones concurrentes sobre F001, entonces se asignan 50 correlativos distintos y sin huecos.
- **AC-2:** Dado un comprobante rechazado con el número 10, entonces la siguiente emisión recibe el 11.
- **AC-3:** Dada la serie `X001`, entonces la creación devuelve 400.

## Contratos
- `GET/POST /series` · `Serie` en [openapi.yaml](../api/openapi.yaml)
