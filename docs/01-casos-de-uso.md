# 01 — Casos de uso

Fuentes:

1. Funcionalidades publicadas por **Nubefact** en su sitio web (sección 6).
2. Problemas de emisión reportados por proveedores de facturación electrónica (sección 5).
3. Necesidades propias de una distribuidora de abarrotes (caso del examen).
4. Verificación con el centro de ayuda oficial de Nubefact, que documenta su sistema web pantalla por pantalla (sección 7).

## 1. Actores

| Actor | Descripción |
|---|---|
| **Vendedor / Cajero** | Emite boletas y facturas desde Windows (caja) o Android (venta en ruta). |
| **Administrador** | Configura empresa, series, productos, usuarios y certificado digital. |
| **Contador** | Consulta, anula, emite notas, descarga XML/CDR, exporta reportes. |
| **Almacenero** | Registra ingresos y salidas (continuidad del legado). |
| **Cliente final** | Recibe el comprobante (PDF + XML) por correo / WhatsApp. |
| **SUNAT / OSE** | Sistema externo que valida y devuelve el CDR. |
| **Padrón RUC** | Fuente externa para consultar estado y condición del contribuyente. |
| **Planificador (sistema)** | Tareas automáticas: resumen diario, reintentos, consulta de estado. |

## 2. Diagrama general

```mermaid
flowchart LR
    V([Vendedor]) --- UC1[UC-01 Emitir factura]
    V --- UC2[UC-02 Emitir boleta]
    V --- UC5[UC-05 Consultar cliente RUC/DNI]
    V --- UC14[UC-14 Enviar comprobante al cliente]
    C([Contador]) --- UC3[UC-03 Emitir nota de crédito]
    C --- UC4[UC-04 Emitir nota de débito]
    C --- UC8[UC-08 Comunicar baja]
    C --- UC9[UC-09 Consultar estado / CDR]
    C --- UC15[UC-15 Reportes de ventas]
    A([Administrador]) --- UC10[UC-10 Gestionar productos]
    A --- UC11[UC-11 Gestionar series]
    A --- UC12[UC-12 Configurar certificado]
    A --- UC13[UC-13 Migrar datos legados]
    AL([Almacenero]) --- UC16[UC-16 Registrar movimiento de almacén]
    P([Planificador]) --- UC7[UC-07 Enviar resumen diario]
    P --- UC6[UC-06 Reenviar pendientes]
    UC1 -. include .-> UCX[Calcular tributos]
    UC2 -. include .-> UCX
    UC1 -. include .-> UCY[Firmar y enviar]
    UC1 -. include .-> UC5
    UCY --- S([SUNAT / OSE])
    UC5 --- PR([Padrón RUC])
```

## 3. Catálogo de casos de uso

Prioridad MoSCoW: **M** = Must, **S** = Should, **C** = Could, **W** = Won't (esta versión).

| ID | Caso de uso | Actor | Prioridad | Spec |
|---|---|---|---|---|
| UC-01 | Emitir factura electrónica | Vendedor | M | SPEC-001, 003, 004, 005, 006, 007 |
| UC-02 | Emitir boleta de venta electrónica | Vendedor | M | SPEC-001, 003, 005, 006 |
| UC-03 | Emitir nota de crédito (anulación, descuento, devolución) | Contador | M | SPEC-002 |
| UC-04 | Emitir nota de débito (intereses, penalidades, aumento de valor) | Contador | M | SPEC-002 |
| UC-05 | Consultar / validar cliente por RUC o DNI | Vendedor | M | SPEC-004 |
| UC-06 | Reenviar comprobantes pendientes o con error de conexión | Planificador | M | SPEC-007 |
| UC-07 | Enviar resumen diario de boletas | Planificador | M | SPEC-008 |
| UC-08 | Comunicar baja de comprobantes | Contador | M | SPEC-008 |
| UC-09 | Consultar estado y descargar XML / CDR / PDF | Contador | M | SPEC-007 |
| UC-10 | Gestionar productos (afectación IGV, ISC, ICBPER, unidad) | Administrador | M | SPEC-003, 010, 011 |
| UC-11 | Gestionar series por establecimiento y tipo de documento | Administrador | M | SPEC-005 |
| UC-12 | Configurar certificado digital y credenciales SOL / OSE | Administrador | M | SPEC-006, 007 |
| UC-13 | Migrar datos históricos del sistema legado | Administrador | M | SPEC-009 |
| UC-14 | Enviar comprobante al cliente (correo / enlace) | Vendedor | S | SPEC-001 |
| UC-15 | Reporte de ventas y registro de ventas | Contador | S | SPEC-001 |
| UC-16 | Registrar movimiento de almacén (ingreso / salida) | Almacenero | M | SPEC-010 |
| UC-17 | Emitir con forma de pago al crédito (cuotas) | Vendedor | S | SPEC-001 |
| UC-18 | Operaciones gratuitas (bonificaciones / muestras) | Vendedor | S | SPEC-003 |
| UC-19 | Venta en ruta sin conexión (Android) y sincronización | Vendedor | S | SPEC-012 |
| UC-20 | Multimoneda (USD) con tipo de cambio | Vendedor | C | SPEC-001 |
| UC-21 | Guía de remisión electrónica | Almacenero | C | — (fase 2) |
| UC-22 | Detracciones, retenciones y percepciones | Contador | W | — (fase 2) |
| UC-23 | Anticipos y exportaciones | Contador | W | — (fase 2) |
| UC-24 | Consulta pública del comprobante por el cliente (web, por RUC/serie/número) | Cliente final | S | SPEC-001 |
| UC-25 | Registrar compras y proveedores (origen de los ingresos al almacén) | Almacenero | C | SPEC-010 |
| UC-26 | Exportar reportes a Excel | Contador | S | SPEC-001 |
| UC-27 | Emitir comprobante de contingencia (cuando no se puede emitir electrónicamente por causas no imputables) | Vendedor | C | — (fase 2) |
| UC-28 | Emitir nota de crédito/débito sobre un comprobante físico o de otro sistema | Contador | C | — (fase 2) |

## 4. Escenarios principales (resumen)

### UC-01 Emitir factura
1. El vendedor ingresa RUC del cliente → el sistema valida dígito verificador y consulta el padrón (UC-05).
2. Agrega ítems; el sistema propone afectación IGV / ISC / ICBPER desde el producto.
3. El sistema calcula tributos y totales (SPEC-003) y muestra la vista previa.
4. El vendedor confirma; el sistema reserva el correlativo (SPEC-005).
5. Se genera el XML UBL 2.1, se firma (SPEC-006) y se envía al OSE / SUNAT (SPEC-007).
6. Se guarda el CDR y se actualiza el estado: `ACEPTADO`, `OBSERVADO` o `RECHAZADO`.
7. Se descuenta stock (SPEC-010) y se ofrece enviar el PDF al cliente (UC-14).

**Alternativos:** RUC con estado *BAJA* o condición *NO HABIDO* → advertencia (bloqueo configurable);
sin conexión → estado `PENDIENTE_ENVIO`, se reintenta (UC-06); rechazo → el correlativo **no se reutiliza**,
se corrige emitiendo un nuevo comprobante.

### UC-02 Emitir boleta
Igual que UC-01, pero el cliente puede ser anónimo si el total no supera el umbral vigente
(S/ 700); si lo supera, el DNI/documento es obligatorio. La boleta se informa por envío
individual o por resumen diario (UC-07).

## 5. Problemas frecuentes en facturación electrónica y requisito derivado

| Problema reportado | Fuente | Requisito derivado |
|---|---|---|
| RUC mal digitado o razón social incompleta invalida la factura | [F2], [F3] | Validación módulo 11 + consulta de padrón (SPEC-004). |
| Tasa de IGV mal aplicada; descuadre entre subtotal y total | [F2], [F3] | Cálculo único en servidor, decimal exacto, tolerancia ±1.00 (SPEC-003). |
| Tipo de cambio no actualizado en moneda extranjera | [F3] | `tipoCambio` obligatorio si moneda ≠ PEN (SPEC-001 R-05). |
| Servidor de SUNAT lento: el emisor reenvía y duplica el correlativo (error 1033) | [F3] | `Idempotency-Key` + consulta de estado antes de reenviar (SPEC-005 R-06, SPEC-007 R-06). |
| Firma inválida o certificado vencido | [F3] | Validación del certificado antes de firmar (SPEC-006 AC-3). |
| Serie o numeración inválida; el número rechazado queda inutilizado | [F2] | Series registradas; correlativo nunca reutilizado (SPEC-005 R-02, R-05). |
| Envío fuera del plazo establecido | [F2] | Reintentos y alerta antes del vencimiento (SPEC-007 R-05). |
| Código de producto SUNAT inválido (observación 4332) | [F3] | Código UNSPSC en el producto (SPEC-010, matriz T-48). |
| Venta en ruta sin internet | Caso del examen | Cola offline en Android (UC-19, SPEC-012). |

## 6. Contraste con Nubefact (funcionalidades publicadas)

| Funcionalidad de Nubefact [F1] | Caso de uso | Resultado |
|---|---|---|
| Facturas, boletas, notas de crédito y débito | UC-01 … UC-04 | Cubierto |
| Anulaciones y reversiones | UC-08 | Cubierto (baja); reversiones de retención/percepción en fase 2 |
| Guías de remisión remitente y transportista | UC-21 | Fase 2 |
| Comprobantes de retención y percepción | UC-22 | Fase 2 |
| Locales y usuarios sin límite | UC-11, actores | Cubierto (series por establecimiento, roles) |
| Representación impresa A4, A5 y ticket, con logotipo | UC-09 | Cubierto (A4 y ticket); A5 a evaluar |
| Módulo de ventas, compras, productos, clientes, proveedores | UC-10, UC-16, **UC-25** | **Agregado** UC-25 (compras y proveedores) |
| Reportes en Excel | **UC-26** | **Agregado** |
| Publicación del comprobante en web / "Busca tu comprobante" | **UC-24** | **Agregado** |
| API REST para integrar otros sistemas | `openapi.yaml` | Cubierto |
| Certificado digital incluido | UC-12 | Cubierto (configuración del certificado) |
| Diseño adaptativo (PC, tablet, celular) | SPEC-012 | Cubierto (Windows + Android) |
| Página de estado del sistema | UC-06 | Cubierto parcialmente (estado `PENDIENTE_ENVIO`) |

Los casos UC-13 (migración del legado), UC-16 (almacén) y UC-19 (venta en ruta offline) no
aparecen en Nubefact: provienen del caso particular de ABC.

Sobre opiniones de usuarios: las fuentes públicas encontradas son escasas y provienen de blogs
de proveedores; la única valoración específica de Nubefact destaca su precio accesible y tiempos
de soporte razonables [F4]. Por eso el catálogo se verificó contra el centro de ayuda oficial de
Nubefact (sección 7), que describe su sistema web pantalla por pantalla.

## 7. Verificación con el centro de ayuda de Nubefact

El registro en Nubefact exige un RUC real, por lo que la verificación se hizo con su centro de
ayuda oficial [F5], que documenta cada pantalla del sistema web. Resultado: **Sí** (confirmado),
**Parcial** (confirmado en parte) o **No verificado** (no figura en el texto público; requiere cuenta).

| # | Qué se revisó | Resultado | Evidencia en Nubefact [F5] | Caso de uso / spec |
|---|---|---|---|---|
| 1 | Menú principal | Sí | Comprobantes, Anulaciones, Resúmenes diarios, Compras, Entidades (clientes y proveedores), Catálogo, Categorías, Reportes, Guías, Retenciones / Percepciones, Contingencia, Integración API, Configuración (empresa, usuarios, locales y series, formato, cuentas bancarias). | Catálogo de la sección 3 |
| 2 | Formulario de factura | Parcial | Comprobantes → Emitir Factura Electrónica: entidad, tipo de operación, ítems, tipo de IGV. Permite guardar como **borrador** y enviarlo después. | UC-01 · estado `BORRADOR` |
| 3 | Validación de RUC y autocompletado | Sí | Al ingresar un RUC ofrece "importar los datos desde SUNAT". | UC-05 · SPEC-004 |
| 4 | Boleta con cliente "varios" y umbral S/ 700 | No verificado | El artículo solo indica Comprobantes → Emitir Boleta de Venta Electrónica. | UC-02 · SPEC-001 R-04 |
| 5 | Ítems: afectación IGV, ISC, ICBPER, unidad | Parcial | Tipo de IGV por ítem; unidades de medida configurables; precio con y sin IGV. ISC e ICBPER no figuran en el texto. | UC-10 · SPEC-003 |
| 6 | Forma de pago crédito con cuotas | No verificado | No figura en el centro de ayuda. | UC-17 · SPEC-001 R-06 |
| 7 | Nota de crédito | Parcial | Desde Comprobantes o desde Opciones del comprobante original; casos: descuento y anulación. También sobre comprobantes **físicos** o de **otro sistema**. | UC-03 · **UC-28** |
| 8 | Nota de débito | Parcial | Mismo flujo que la nota de crédito; tipos no listados en el texto. | UC-04 · SPEC-002 |
| 9 | Anulación / comunicación de baja | Sí | Requiere CDR **aceptado**; plazo **7 días** desde la emisión; desde el comprobante o el panel Anulaciones; vencido el plazo se emite nota de crédito. | UC-08 · SPEC-008 R-04 |
| 10 | Resumen diario de boletas | Sí | Se genera **automáticamente cada 24 horas**; estado SUNAT visible por colores. | UC-07 · SPEC-008 R-02 |
| 11 | Estados y descarga de XML / CDR / PDF | Parcial | Estado SUNAT visible en resúmenes y comprobantes; la descarga de XML/CDR no figura en el texto. | UC-09 · SPEC-007 |
| 12 | Envío al cliente | Sí | Solo por **correo**, al registrado o a otro, y solo si SUNAT ya aceptó el comprobante. | UC-14 |
| 13 | Series y establecimientos | Sí | Configuración → Locales y series: código SUNAT del local (`0000` si hay uno), ubigeo, usuario encargado; series F (facturas y sus notas), B (boletas y sus notas), T y V (guías). | UC-11 · SPEC-005 R-01 · matriz T-15 |
| 14 | Reportes | Sí | Excel por rango de fechas, por **ítems** o por **documentos**, de un local o de todos. | UC-15 · UC-26 |
| 15 | Productos, clientes, compras y proveedores | Sí | Catálogo con categorías; Entidades (clientes y proveedores); Compras → Agregar compra, exportable a Excel. No se menciona control de stock. | UC-10 · UC-25 |
| 16 | Contingencia | Sí | Comprobante de contingencia cuando no se puede emitir electrónicamente por causas no imputables al emisor. | **UC-27** |

**Conclusiones**

- De 16 puntos: **9 confirmados**, **5 parciales** (2, 5, 7, 8, 11) y **2 no verificados** (4, 6). Ninguno contradice el catálogo; los hallazgos nuevos se agregaron como **UC-27** y **UC-28**.
- Según su documentación, Nubefact **no controla stock**: el inventario integrado a ventas (SPEC-010) y la migración del legado (SPEC-009) son necesidades propias de ABC.
- Los puntos parciales y no verificados se completarían con una cuenta registrada con RUC.

## 8. Referencias

- [F1] Nubefact — sitio oficial y Nubefact Online: <https://www.nubefact.com>, <https://www.nubefact.com/nubefact-online>
- [F2] Nubefact — "¿Tu factura electrónica fue rechazada por SUNAT? Conoce los motivos y qué hacer": <https://www.nubefact.com/blog/facturacion-electronica/tu-factura-electronica-fue-rechazada-por-sunat-conoce-los-motivos-y-que-hacer>
- [F3] Errores frecuentes reportados por proveedores: <https://bizlinks.com.pe/errores-frecuentes-en-la-facturacion-electronica-sunat/>, <https://acepta.com/pe/blog/errores-en-facturacion-electronica/>, <https://perusoftware.net.pe/blog/errores-sunat-codigos-significado-solucion>, <https://www.nubefact.com/codigos-error-sunat>
- [F4] kom.pe — "Cómo emitir boletas y facturas SUNAT desde WooCommerce": <https://kom.pe/como-emitir-boletas-y-facturas-sunat-desde-woocommerce/>
- [F5] Centro de ayuda de Nubefact — preguntas frecuentes de NubeFact Web: <https://ayuda.nubefact.com/preguntas/nubefact-web>. Artículos usados: emitir factura, emitir boleta, emitir nota de crédito / débito, en qué momento generar una nota de crédito, anular / comunicar de baja una factura, plazos de baja, resúmenes diarios automáticos, locales y series, catálogo de productos, compras, reportes, envío al cliente y contingencia.
