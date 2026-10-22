# FEAT-001: Exportar guías de remisión a Excel

- **Status:** Draft
- **Author:** crissdav
- **Date:** 2026-10-22
- **Related:** API-001 (`specs/api/001-guias-remision.yaml`, operación `exportar_guias_remision_excel`)

## Summary
Permitir descargar en un archivo Excel (`.xlsx`) las guías de remisión electrónicas
que cumplan los filtros indicados, con su cabecera y el detalle de los bienes trasladados.

## Motivation
Las áreas de logística, almacén y contabilidad necesitan revisar los despachos fuera
del sistema: conciliar guías con facturas, controlar qué vehículos salieron, y
revisar las guías rechazadas u observadas por SUNAT. Hoy solo pueden consultarlas
una por una o mediante la lista paginada.

## Scope
### In scope
- Exportar a `.xlsx` usando los mismos filtros que el listado de guías
  (`estado`, `serie`, `ruc_destinatario`, `fecha_desde`, `fecha_hasta`, `placa`).
- Una hoja con una fila por guía y otra hoja con una fila por ítem.
- Descarga directa en la respuesta HTTP (síncrona).
- Acceso restringido al rol `superadmin`.

### Out of scope
- Otros formatos (CSV, PDF).
- Exportación asíncrona o por correo para volúmenes grandes.
- Elegir las columnas o su orden.
- Incluir los XML, CDR o PDF de las guías.

## Behavior

### Endpoint
`GET /api/v1/guias-remision/exportar` con los mismos parámetros de filtro que
`GET /api/v1/guias-remision` (sin `page` ni `size`).

### Archivo
- Tipo: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.
- Cabecera `Content-Disposition: attachment; filename="guias-remision_AAAAMMDD-HHMMSS.xlsx"`
  (fecha y hora de generación, zona horaria America/Lima).
- Guías ordenadas por `fecha_emision` descendente y luego por `serie_numero`.

### Hoja 1 – `Guias`
| Columna | Origen |
|---|---|
| Serie-Número | `serie_numero` (vacío si aún no se emitió) |
| Fecha emisión | `fecha_emision` (formato fecha de Excel) |
| Estado | `estado` |
| RUC remitente | `remitente.numero_documento` |
| Destinatario – Doc. | `destinatario.numero_documento` |
| Destinatario – Razón social | `destinatario.razon_social` |
| Motivo de traslado | código + descripción del catálogo N° 20 |
| Modalidad | código + descripción del catálogo N° 18 |
| Fecha inicio traslado | `fecha_inicio_traslado` |
| Punto de partida | `ubigeo` – `direccion` |
| Punto de llegada | `ubigeo` – `direccion` |
| Transportista RUC | `transportista.ruc` |
| Placas | placas de `vehiculos` separadas por coma |
| Conductor principal | nombres, apellidos y licencia del conductor principal |
| Peso bruto | `peso_bruto_total` (numérico) |
| Unidad peso | `unidad_peso` |
| N° bultos | `numero_bultos` |
| Documentos relacionados | `serie_numero` separados por coma |
| Código respuesta SUNAT | `sunat.codigo_respuesta` |
| Descripción respuesta SUNAT | `sunat.descripcion_respuesta` |

### Hoja 2 – `Items`
| Columna | Origen |
|---|---|
| Serie-Número | guía a la que pertenece |
| Código | `items[].codigo` |
| Descripción | `items[].descripcion` |
| Cantidad | `items[].cantidad` (numérico) |
| Unidad de medida | `items[].unidad_medida` |

### Formato
- Fila de encabezado en negrita, inmovilizada y con autofiltro.
- Las fechas y los números se guardan como tipos nativos de Excel, no como texto.
- Los RUC, DNI y ubigeos se guardan como texto (para no perder ceros a la izquierda).

### Autorización
- Solo los usuarios con rol **`superadmin`** pueden exportar.
- Sin autenticación (token ausente o inválido) se responde `401`.
- Usuario autenticado sin rol `superadmin` se responde `403` con código
  `EXPORTACION_NO_AUTORIZADA`.
- La autorización se verifica **antes** de consultar las guías.

### Límite
Máximo **100 guías** por exportación. Si los filtros devuelven más, se responde
`422` con código `EXPORTACION_EXCEDE_LIMITE` y no se genera el archivo; el usuario
debe acotar los filtros (por ejemplo, el rango de fechas).

## Acceptance Criteria
- **AC-1:** Dado que existen guías que cumplen los filtros, cuando se llama a
  `GET /guias-remision/exportar`, entonces la respuesta es `200` con un `.xlsx` válido
  que contiene las hojas `Guias` e `Items`.
- **AC-2:** Dado un filtro (por ejemplo `estado=ACEPTADA` y un rango de fechas), cuando
  se exporta, entonces la hoja `Guias` contiene exactamente las mismas guías que
  devolvería `GET /guias-remision` con esos filtros.
- **AC-3:** Dada una guía con N ítems, cuando se exporta, entonces la hoja `Items`
  contiene N filas con su `Serie-Número`.
- **AC-4:** Dado que ninguna guía cumple los filtros, cuando se exporta, entonces la
  respuesta es `200` con un archivo que solo contiene los encabezados.
- **AC-5:** Dado que los filtros devuelven más de 100 guías, cuando se exporta,
  entonces la respuesta es `422` con código `EXPORTACION_EXCEDE_LIMITE`.
  Con exactamente 100 guías la exportación es exitosa.
- **AC-6:** Dado `fecha_desde` posterior a `fecha_hasta`, cuando se exporta, entonces
  la respuesta es `422`.
- **AC-7:** Cuando se exporta, la respuesta incluye `Content-Type` de Excel y un
  `Content-Disposition` con el nombre `guias-remision_AAAAMMDD-HHMMSS.xlsx`.
- **AC-8:** Dado un RUC o ubigeo que empieza con cero, cuando se exporta, entonces
  la celda conserva el cero inicial.
- **AC-9:** Dado un usuario autenticado sin rol `superadmin`, cuando exporta, entonces
  la respuesta es `403` con código `EXPORTACION_NO_AUTORIZADA` y no se genera el archivo.
- **AC-10:** Dada una petición sin token o con token inválido, cuando se exporta,
  entonces la respuesta es `401`.

## Edge Cases & Errors
- Guías en `BORRADOR` sin número: la columna `Serie-Número` va vacía; en la hoja
  `Items` se usa la `serie` seguida de `(borrador)`.
- Guías sin transportista, vehículos o conductores: las celdas quedan vacías.
- Textos con caracteres especiales (ñ, tildes) o que empiezan con `=`, `+`, `-`, `@`:
  se escriben como texto para evitar inyección de fórmulas.

## Implementation Notes
- Librería sugerida: `openpyxl`.
- La verificación de rol puede implementarse como dependencia de FastAPI
  (p. ej. `Depends(requiere_rol("superadmin"))`).
- Contar las guías antes de cargarlas para aplicar el límite de 100 sin traerlas todas.
- En FastAPI, la ruta `/guias-remision/exportar` debe registrarse **antes** que
  `/guias-remision/{guia_id}` para que no se interprete `exportar` como un id.
- Reutilizar la misma función de filtrado que usa `listar_guias_remision`.

## Open Questions
- El sistema de autenticación (emisión del token y gestión de roles) aún no está
  especificado; esta funcionalidad depende de él.
