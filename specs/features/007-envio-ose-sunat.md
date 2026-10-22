# SPEC-007: Envío a OSE / SUNAT y gestión del CDR

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-06, UC-09 · ADR-003 · [respuesta-cdr.schema.json](../schemas/respuesta-cdr.schema.json)

## Resumen
Enviar el comprobante firmado al OSE o a SUNAT, interpretar el CDR y gestionar reintentos.

## Reglas
| ID | Regla |
|---|---|
| R-01 | Canal configurable por empresa: `SUNAT` (SEE del contribuyente) u `OSE`. Ambos detrás de `EnvioSunatPort`. |
| R-02 | Facturas y sus notas: envío individual síncrono (`sendBill`). |
| R-03 | Interpretación del código de respuesta: `0` → ACEPTADO; ≥ `4000` → OBSERVADO (aceptado con observaciones); `2000`–`3999` → RECHAZADO; `0100`–`1999` → EXCEPCION (reintentable, estado `PENDIENTE_ENVIO`). |
| R-04 | Un comprobante no puede tener dos envíos simultáneos (`ENVIO_EN_CURSO`). |
| R-05 | Reintentos automáticos con backoff exponencial (1, 5, 15, 60 min…) dentro del plazo máximo de envío vigente; alerta al contador al acercarse el vencimiento. |
| R-06 | Antes de reenviar tras un timeout se consulta el estado (`getStatus`) para no duplicar envíos. |
| R-07 | El CDR se guarda tal cual (ZIP) junto al XML firmado. |
| R-08 | Un comprobante RECHAZADO no se corrige ni se reenvía: se emite uno nuevo con otro correlativo. |

## Criterios de aceptación
- **AC-1:** Dado un CDR con código 0, entonces estado `ACEPTADO` y evento `ComprobanteAceptado`.
- **AC-2:** Dado un CDR con código 2800, entonces estado `RECHAZADO` y error `SUNAT-2800`.
- **AC-3:** Dado un timeout del OSE, entonces estado `PENDIENTE_ENVIO` y respuesta HTTP 202.
- **AC-4:** Dado un comprobante `PENDIENTE_ENVIO`, cuando el planificador reintenta y SUNAT responde 0, entonces pasa a `ACEPTADO`.

## Preguntas abiertas
- Selección del OSE (proveedor) y su contrato SOAP específico.
