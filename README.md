# ABC Software Corp — Facturación Electrónica SUNAT (Spec-First)

**primera fase (Spec-First)**: especificaciones técnicas definidas antes de
escribir lógica de negocio. No contiene código de implementación.

## 1. Resumen de lo realizado

| Fase | Resultado |
|---|---|
| **Entender** | Análisis del caso: el legado es un control de almacén (`fecha, ingreso, salida, producto, nro_documento`) sin validación de RUC, cálculo de tributos, XML UBL ni conexión con SUNAT/OSE. Base normativa: RS 097-2012, RS 234-2006, catálogos SUNAT (énfasis en el **catálogo 08 — ISC**) y UBL 2.1 de OASIS. |
| **Planificar** | 12 specs funcionales derivadas de cada vacío del enunciado, 3 decisiones de arquitectura (ADR) y estructura `docs/` + `specs/`. |
| **Actuar** | 4 entregables del examen + casos de uso, migración del legado, 12 JSON Schemas, 11 catálogos y contrato OpenAPI. |
| **Validar** | Script automático con 435 verificaciones, lint de OpenAPI y renderizado de los 10 diagramas. Corrigió 2 errores de cálculo en el ejemplo de factura. |

**Decisiones clave**

- **MVC por fuera, hexagonal por dentro:** el MVC vive solo en la capa de entrega; el modelo es un
  núcleo de dominio con puertos, por lo que migrar a Hexagonal / microservicios es reorganizar, no reescribir.
- **ISC (catálogo 08):** se calcula antes del IGV porque forma parte de su base; el ejemplo de
  factura usa cerveza (monto fijo, 02) y gaseosa (al valor, 01).
- **Legado:** se migra con hash por fila para trazabilidad; `nro_documento` nunca se convierte en correlativo SUNAT.
- **Montos como string decimal** para evitar errores de redondeo de punto flotante.
- **Stack recomendado:** Kotlin Multiplatform (MSI + APK) y Spring Boot; firma digital solo en servidor.

## 2. Entregables del examen

| Entregable | Dónde está |
|---|---|
| 1. Modelo de Dominio y Contratos (DTOs / Schemas) | [docs/02-modelo-dominio.md](docs/02-modelo-dominio.md) · [specs/schemas/](specs/schemas/) · [specs/catalogos/](specs/catalogos/) |
| 2. Diagramas de Arquitectura MVC con visión a Hexagonal | [docs/03-arquitectura.md](docs/03-arquitectura.md) · [docs/adr/](docs/adr/) |
| 3. Especificación de Endpoints / Servicios | [docs/04-contratos-api.md](docs/04-contratos-api.md) · [specs/api/openapi.yaml](specs/api/openapi.yaml) |
| 4. Matriz de Trazabilidad Normativa SUNAT ↔ UBL | [docs/05-matriz-trazabilidad.md](docs/05-matriz-trazabilidad.md) |

Soporte: [contexto y normativa](docs/00-contexto.md) · [casos de uso](docs/01-casos-de-uso.md) ·
[migración del legado](docs/06-migracion-legado.md) · [referencia UBL](specs/ref/README.md).

## 3. Specs funcionales

| ID | Spec |
|---|---|
| [SPEC-001](specs/features/001-emision-factura-boleta.md) | Emisión de Factura y Boleta |
| [SPEC-002](specs/features/002-notas-credito-debito.md) | Notas de Crédito y Débito |
| [SPEC-003](specs/features/003-calculo-tributos.md) | Cálculo de tributos (IGV, ISC cat. 08, ICBPER) |
| [SPEC-004](specs/features/004-validacion-identidad.md) | Validación de RUC / DNI |
| [SPEC-005](specs/features/005-series-correlativos.md) | Series y correlativos |
| [SPEC-006](specs/features/006-xml-ubl-firma.md) | XML UBL 2.1 y firma digital |
| [SPEC-007](specs/features/007-envio-ose-sunat.md) | Envío a OSE / SUNAT y CDR |
| [SPEC-008](specs/features/008-resumen-diario-baja.md) | Resumen diario y comunicación de baja |
| [SPEC-009](specs/features/009-migracion-legado.md) | Migración de datos legados |
| [SPEC-010](specs/features/010-inventario.md) | Inventario integrado a ventas |
| [SPEC-011](specs/features/011-catalogos-sunat.md) | Catálogos SUNAT |
| [SPEC-012](specs/features/012-distribucion-multiplataforma.md) | Distribución MSI / APK |

ADR: [001 Stack](docs/adr/001-stack-multiplataforma.md) ·
[002 Monolito MVC con puertos](docs/adr/002-monolito-mvc-con-puertos.md) ·
[003 Firma en servidor](docs/adr/003-firma-y-envio-en-servidor.md).

## 4. Validación

```bash
npm install
npm run validate        # esquemas, ejemplos, aritmética SPEC-003, matriz, enlaces y lint OpenAPI
npm run check:mermaid   # renderiza los diagramas (usa Chrome/Edge instalado o CHROME_PATH)
```

## 5. Pendientes para la siguiente fase

- Confirmar contra la norma vigente: plazos de envío y baja, umbral de boletas (S/ 700) e ICBPER (S/ 0.50).
- Las tasas ISC del ejemplo son ilustrativas.
- Contrastar los casos de uso con un usuario DEMO de Nubefact.
- Detallar resumen diario y baja (SPEC-008) y el catálogo completo de errores SUNAT.
