# SPEC-008: Resumen diario de boletas y comunicación de baja

- **Estado:** Draft (esqueleto — detalle en fase 2)
- **Fecha:** 2026-10-22
- **Relacionado:** UC-07, UC-08 · SPEC-007 · [comunicacion-baja.schema.json](../schemas/comunicacion-baja.schema.json)

## Resumen
Generar y enviar de forma asíncrona (`sendSummary` → ticket → `getStatus`):
- **Resumen diario (RC)**: informa las boletas y sus notas de un día.
- **Comunicación de baja (RA)**: anula comprobantes aceptados que no debieron emitirse.

## Reglas
| ID | Regla |
|---|---|
| R-01 | Identificador: `RC-AAAAMMDD-n` / `RA-AAAAMMDD-n` (n correlativo diario). |
| R-02 | El planificador genera el RC del día anterior automáticamente; también puede lanzarse manualmente. |
| R-03 | Una boleta ya informada individualmente no se vuelve a incluir en un RC como "adicionar". |
| R-04 | La baja solo procede sobre comprobantes ACEPTADOS/OBSERVADOS, dentro del plazo vigente, y no aplica si el bien ya fue entregado (en ese caso: nota de crédito tipo 01). |
| R-05 | Al confirmar el ticket, los comprobantes de la baja pasan a `ANULADO` y se revierte el stock (SPEC-010). |
| R-06 | Los plazos (envío de RC, comunicación de baja) son parámetros con vigencia. Valor de referencia para la baja: **7 días calendario** desde la emisión; vencido el plazo, se emite nota de crédito (según el centro de ayuda de Nubefact, ver [casos de uso §7](../../docs/01-casos-de-uso.md)). |

## Criterios de aceptación
- **AC-1:** Dadas 30 boletas del 21/10, cuando corre el planificador el 22/10, entonces se envía `RC-20261022-1` y se guarda el ticket.
- **AC-2:** Dado un ticket con CDR código 0, entonces los comprobantes de la baja quedan `ANULADO`.
- **AC-3:** Dada una baja de un comprobante `RECHAZADO`, entonces 400.
