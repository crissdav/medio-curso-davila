# SPEC-004: Validación de identidad del cliente (RUC / DNI)

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-05 · Catálogo 06 · SPEC-001

## Resumen
Validar el formato y el dígito verificador de los documentos de identidad, y consultar el estado
y la condición del contribuyente en el padrón RUC.

## Motivación
El sistema actual "no valida RUCs": se emiten facturas a RUC inexistentes, que SUNAT rechaza.

## Reglas de negocio
| ID | Regla |
|---|---|
| R-01 | **RUC**: 11 dígitos, prefijo `10`, `15`, `16`, `17` o `20`, y dígito verificador **módulo 11**: pesos `5,4,3,2,7,6,5,4,3,2` sobre los 10 primeros dígitos; `r = 11 − (Σ mod 11)`; si `r = 10` → `0`, si `r = 11` → `1`; `r` debe ser igual al dígito 11. |
| R-02 | **DNI**: 8 dígitos numéricos. Otros documentos: patrón del catálogo 06. |
| R-03 | Consulta de padrón: si el estado ≠ `ACTIVO` o la condición = `NO HABIDO` → advertencia `CLIENTE_NO_HABIDO` (bloqueo configurable por la empresa). |
| R-04 | El padrón se consulta con caché local (TTL 24 h); si el servicio externo falla se usa el último dato con `fuente = PADRON_LOCAL`. |
| R-05 | La validación de formato y módulo 11 se ejecuta también en el cliente (módulo `shared`) para respuesta inmediata; el servidor la repite siempre. |

## Criterios de aceptación
- **AC-1:** RUC `20123456786` → válido. RUC `20123456787` → `RUC_INVALIDO`.
- **AC-2:** RUC `30123456786` → inválido por prefijo.
- **AC-3:** DNI `1234567` → inválido (7 dígitos).
- **AC-4:** Dado un RUC con condición NO HABIDO y política "advertir", cuando emito factura, entonces se emite y la respuesta incluye la advertencia.
- **AC-5:** Dado el servicio de padrón caído, cuando consulto un RUC en caché, entonces respondo 200 con `fuente = PADRON_LOCAL`.

## Contratos
- `GET /contribuyentes/{ruc}`, `POST /documentos-identidad/validaciones` · [cliente.schema.json](../schemas/cliente.schema.json)
