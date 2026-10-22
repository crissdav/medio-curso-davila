# SPEC-009: Migración de datos legados

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-13 · INV-09 · RS 234-2006/SUNAT · [06-migracion-legado.md](../../docs/06-migracion-legado.md)

## Resumen
Migrar las fichas de almacén (`fecha, ingreso, salida, producto, nro_documento`) a las entidades
`Producto` y `MovimientoInventario` **sin perder trazabilidad**.

## Reglas de transformación (M-n)
| ID | Regla |
|---|---|
| M-01 | Cada fila origen recibe un `hashOrigen` = SHA-256 de la fila cruda normalizada + número de fila; queda en `OrigenDato`. |
| M-02 | `fecha`: se aceptan `dd/mm/aaaa`, `aaaa-mm-dd`, `dd-mm-aa`; se convierte a ISO-8601. Fecha nula, inválida o futura → cuarentena. |
| M-03 | `ingreso` > 0 y `salida` vacía → movimiento `INGRESO`; `salida` > 0 e `ingreso` vacío → `SALIDA`; ambos > 0 → **dos** movimientos con el mismo `hashOrigen`; ambos vacíos o 0 → cuarentena. Valores negativos o no numéricos → cuarentena. |
| M-04 | `producto`: se normaliza (trim, mayúsculas, espacios simples, sin tildes) y se agrupa; cada nombre normalizado distinto crea un `Producto` con código generado, `afectacionIgv = 10` y `unidad = NIU` **provisionales** y marca `requiereRevision = true` (la configuración tributaria la confirma el administrador antes de vender). |
| M-05 | `nro_documento` → `documentoReferencia` con tipo `INTERNO_LEGADO`. **Nunca** se convierte en serie/correlativo SUNAT ni se generan comprobantes electrónicos retroactivos. |
| M-06 | Re-ejecutar el mismo lote es **idempotente**: filas con `hashOrigen` ya migrado se omiten. |
| M-07 | Modo simulación (*dry-run*) por defecto: reporta resultados sin persistir. |
| M-08 | Conciliación obligatoria al cerrar el lote: Σ ingresos y Σ salidas origen = destino (por producto y total); stock final por producto = Σ ingresos − Σ salidas. Si no cuadra → `COMPLETADO_CON_INCIDENCIAS`. |
| M-09 | El origen es de solo lectura: la migración nunca modifica el sistema legado. |

## Criterios de aceptación
- **AC-1:** Dado [legacy-movimiento.json](../schemas/examples/legacy-movimiento.json), cuando migro, entonces obtengo [movimiento-inventario.json](../schemas/examples/movimiento-inventario.json) (SALIDA de 12 de `CER-620`, referencia `N-0458`, origen LEGADO).
- **AC-2:** Dada una fila con ingreso y salida vacíos, entonces queda en cuarentena con regla `SPEC-009/M-03`.
- **AC-3:** Dado el mismo archivo cargado dos veces, entonces la segunda carga migra 0 filas.
- **AC-4:** Dado un lote completado, entonces la conciliación muestra sumas origen = destino.
- **AC-5:** Dado un movimiento migrado, cuando consulto su `hashOrigen`, entonces puedo ubicar la fila exacta del archivo legado.

## Contratos
- `POST /migraciones`, `GET /migraciones/{lote}`, `GET /migraciones/{lote}/incidencias`
- [legacy-movimiento.schema.json](../schemas/legacy-movimiento.schema.json) → [movimiento-inventario.schema.json](../schemas/movimiento-inventario.schema.json)
