# 04 — Especificación de endpoints y servicios (contratos API)

> Entregable 3 del examen. Contrato ejecutable: [specs/api/openapi.yaml](../specs/api/openapi.yaml)
> (OpenAPI 3.1, referencia los JSON Schemas de `specs/schemas/`).

## 1. Convenciones

| Aspecto | Regla |
|---|---|
| Base | `/api/v1` — versión en la ruta |
| Formato | JSON UTF-8; montos como string decimal |
| Autenticación | Bearer JWT (roles: VENDEDOR, CONTADOR, ADMIN, ALMACENERO) |
| Idempotencia | `Idempotency-Key` obligatoria en emisiones (no se consumen dos correlativos en un reintento) |
| Errores | `application/problem+json` con `codigo` de negocio o `SUNAT-nnnn` |
| Paginación | `pagina`, `tamanio` (máx. 200) |

## 2. Endpoints (adaptadores de entrada MVC → puertos de entrada)

| Método y ruta | Caso de uso (puerto de entrada) | Rol | Spec |
|---|---|---|---|
| `POST /comprobantes` | `EmitirComprobanteUseCase` | VENDEDOR | 001 |
| `GET /comprobantes` | `ConsultarComprobantesQuery` | CONTADOR | 001 |
| `GET /comprobantes/{id}` | `ConsultarComprobantesQuery` | VENDEDOR, CONTADOR | 001 |
| `GET /comprobantes/{id}/xml` | `DescargarArchivoQuery` | CONTADOR | 006 |
| `GET /comprobantes/{id}/cdr` | `DescargarArchivoQuery` | CONTADOR | 007 |
| `GET /comprobantes/{id}/pdf` | `GenerarRepresentacionImpresaUseCase` | VENDEDOR | 001 |
| `POST /comprobantes/{id}/reenvios` | `ReenviarComprobanteUseCase` | CONTADOR, sistema | 007 |
| `POST /notas` | `EmitirNotaUseCase` | CONTADOR | 002 |
| `POST /tributos/calculos` | `CalcularTributosUseCase` | VENDEDOR | 003 |
| `GET /contribuyentes/{ruc}` | `ConsultarContribuyenteUseCase` | VENDEDOR | 004 |
| `POST /documentos-identidad/validaciones` | `ValidarDocumentoUseCase` | VENDEDOR | 004 |
| `GET/POST /series` | `GestionarSeriesUseCase` | ADMIN | 005 |
| `POST /resumenes-diarios` | `EnviarResumenDiarioUseCase` | sistema, CONTADOR | 008 |
| `POST /comunicaciones-baja` | `ComunicarBajaUseCase` | CONTADOR | 008 |
| `GET /tickets/{ticket}` | `ConsultarTicketUseCase` | sistema, CONTADOR | 008 |
| `GET/POST /productos` | `GestionarProductosUseCase` | ADMIN | 010 |
| `GET/POST /inventario/movimientos` | `RegistrarMovimientoUseCase` | ALMACENERO | 010 |
| `POST /migraciones` | `MigrarLegadoUseCase` | ADMIN | 009 |
| `GET /migraciones/{lote}` | `ConsultarLoteQuery` | ADMIN | 009 |
| `GET /migraciones/{lote}/incidencias` | `ConsultarLoteQuery` | ADMIN | 009 |
| `GET /catalogos/{numero}` | `ConsultarCatalogoQuery` | todos | 011 |

## 3. Puertos de salida (contratos de servicios internos)

Interfaces que el núcleo **exige** y que la infraestructura implementa. Son los contratos que
permiten cambiar SUNAT por OSE, PostgreSQL por otra base, o un módulo local por un microservicio.

```kotlin
// application/port/out — firmas de referencia (no es implementación)

interface SerieRepository {
    /** Reserva atómicamente el siguiente correlativo (bloqueo por serie). INV-05 */
    fun siguienteCorrelativo(ruc: Ruc, tipo: TipoComprobante, serie: String): Long
}

interface ComprobanteRepository {
    fun guardar(c: Comprobante)
    fun buscarPorNumero(ruc: Ruc, tipo: TipoComprobante, numero: NumeroComprobante): Comprobante?
    fun buscarPorIdempotencia(clave: UUID): Comprobante?
    fun pendientesDeEnvio(limite: Int): List<Comprobante>
}

interface PadronRucPort {
    /** Estado (ACTIVO, BAJA…) y condición (HABIDO, NO HABIDO). Puede responder desde caché. */
    fun consultar(ruc: Ruc): Contribuyente?
}

interface GeneradorUblPort {
    /** Traduce el agregado a XML UBL 2.1 según la matriz de trazabilidad. */
    fun generar(c: Comprobante): XmlDocumento
}

interface FirmaDigitalPort {
    /** XMLDSig enveloped en ext:UBLExtensions; devuelve XML firmado + DigestValue (hash). */
    fun firmar(xml: XmlDocumento): XmlFirmado
}

interface EnvioSunatPort {   // implementaciones: SunatAdapter, OseAdapter
    fun enviarComprobante(zip: ArchivoZip): Cdr            // sendBill (síncrono)
    fun enviarResumen(zip: ArchivoZip): Ticket            // sendSummary (asíncrono)
    fun consultarTicket(ticket: Ticket): Cdr              // getStatus
}

interface AlmacenArchivosPort {
    fun guardar(ruta: String, contenido: ByteArray)
    fun leer(ruta: String): ByteArray
}

interface FuenteLegadoPort {
    fun leerFilas(lote: LoteMigracion): Sequence<FilaLegado>
}

interface CatalogoPort {
    fun codigoVigente(catalogo: String, codigo: String, fecha: LocalDate): CodigoCatalogo?
}
```

## 4. Contratos con sistemas externos

| Sistema | Protocolo | Operaciones | Adaptador |
|---|---|---|---|
| SUNAT SEE | SOAP (WS-Security usuario SOL) | `sendBill`, `sendSummary`, `getStatus` | `SunatAdapter` |
| OSE | SOAP compatible con SUNAT (según operador) | ídem | `OseAdapter` |
| Padrón RUC | Archivo padrón reducido (descarga diaria) o servicio externo | consulta por RUC | `PadronRucAdapter` |
| Legado | CSV / volcado de la base actual | lectura por lote | `LegacyCsvAdapter` |

Archivo enviado: `{RUC}-{TIPO}-{SERIE}-{CORRELATIVO}.zip` con el XML de igual nombre
(p.ej. `20123456786-01-F001-123.zip`).

## 5. Códigos de error de negocio

| Código | HTTP | Regla |
|---|---|---|
| `RUC_INVALIDO` | 400 | SPEC-004 R-01 (módulo 11) |
| `CLIENTE_NO_HABIDO` | 400 / advertencia | SPEC-004 R-03 |
| `CLIENTE_REQUERIDO_BOLETA` | 400 | SPEC-001 R-04 (umbral S/ 700) |
| `SERIE_NO_AUTORIZADA` | 400 | SPEC-005 R-02 |
| `SERIE_INCOMPATIBLE` | 400 | SPEC-002 R-02 |
| `ISC_CONFIGURACION_INCOMPLETA` | 400 | SPEC-003 R-05 |
| `TOTALES_DESCUADRADOS` | 400 | SPEC-003 R-09 |
| `COMPROBANTE_INMUTABLE` | 409 | INV-06 |
| `ENVIO_EN_CURSO` | 409 | SPEC-007 R-04 |
| `SUNAT-nnnn` | 422 | Rechazo de SUNAT/OSE (2000-3999) |
