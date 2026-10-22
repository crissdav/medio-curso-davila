# 01 — Casos de uso

Fuentes:

1. Funcionalidades publicadas por **Nubefact** en su sitio web (sección 6).
2. Problemas de emisión reportados por proveedores de facturación electrónica (sección 5).
3. Necesidades propias de una distribuidora de abarrotes (caso del examen).
4. Verificación con cuenta DEMO de Nubefact (sección 7).

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
de soporte razonables [F4]. Por eso la verificación directa con la cuenta DEMO (sección 7) es la
fuente principal para validar el catálogo.

## 7. Verificación con cuenta DEMO de Nubefact

Completar al revisar la cuenta DEMO (marcar Sí / No y anotar lo nuevo):

| # | Qué revisar en Nubefact | ¿Existe? | Caso de uso | Observación |
|---|---|---|---|---|
| 1 | Menú principal: lista completa de opciones | | — | |
| 2 | Formulario de factura: campos obligatorios y opcionales | | UC-01 | |
| 3 | ¿Valida el RUC y autocompleta la razón social? | | UC-05 | |
| 4 | Boleta: ¿permite cliente "varios" y desde qué monto lo exige? | | UC-02 | |
| 5 | Ítems: afectación IGV, ISC, ICBPER, unidad de medida | | UC-10 | |
| 6 | Forma de pago crédito con cuotas | | UC-17 | |
| 7 | Nota de crédito: tipos disponibles (catálogo 09) | | UC-03 | |
| 8 | Nota de débito: tipos disponibles (catálogo 10) | | UC-04 | |
| 9 | Anulación / comunicación de baja | | UC-08 | |
| 10 | Resumen diario de boletas (¿automático o manual?) | | UC-07 | |
| 11 | Estados del comprobante y descarga de XML / CDR / PDF | | UC-09 | |
| 12 | Envío por correo al cliente | | UC-14 | |
| 13 | Gestión de series y establecimientos | | UC-11 | |
| 14 | Reportes disponibles | | UC-15, UC-26 | |
| 15 | Productos, clientes, compras y proveedores | | UC-10, UC-25 | |

## 8. Referencias

- [F1] Nubefact — sitio oficial y Nubefact Online: <https://www.nubefact.com>, <https://www.nubefact.com/nubefact-online>
- [F2] Nubefact — "¿Tu factura electrónica fue rechazada por SUNAT? Conoce los motivos y qué hacer": <https://www.nubefact.com/blog/facturacion-electronica/tu-factura-electronica-fue-rechazada-por-sunat-conoce-los-motivos-y-que-hacer>
- [F3] Errores frecuentes reportados por proveedores: <https://bizlinks.com.pe/errores-frecuentes-en-la-facturacion-electronica-sunat/>, <https://acepta.com/pe/blog/errores-en-facturacion-electronica/>, <https://perusoftware.net.pe/blog/errores-sunat-codigos-significado-solucion>, <https://www.nubefact.com/codigos-error-sunat>
- [F4] kom.pe — "Cómo emitir boletas y facturas SUNAT desde WooCommerce": <https://kom.pe/como-emitir-boletas-y-facturas-sunat-desde-woocommerce/>
