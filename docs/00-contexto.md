# 00 — Contexto, alcance y base normativa

## 1. Caso

**ABC Software Corp** comercializa abarrotes y mercadería al por mayor y menor. Su software actual
solo registra el día a día del almacén mediante fichas informales:

| Campo legado | Significado |
|---|---|
| `fecha` | Fecha del movimiento |
| `ingreso` | Cantidad que entra al almacén |
| `salida` | Cantidad que sale del almacén |
| `producto` | Nombre libre del producto (texto, sin código) |
| `nro_documento` | Número de documento **interno** (no es un comprobante SUNAT) |

### Vacíos detectados frente a la normativa

| Vacío | Consecuencia | Spec que lo resuelve |
|---|---|---|
| No valida RUC | Facturas emitidas a contribuyentes inexistentes o con dígito verificador inválido → rechazo | SPEC-004 |
| No calcula IGV / ISC / ICBPER | Totales incorrectos → rechazo SUNAT o contingencia tributaria | SPEC-003 |
| No genera XML UBL | No existe comprobante electrónico legal | SPEC-001, SPEC-002, SPEC-006 |
| No firma digitalmente | El XML no tiene validez | SPEC-006 |
| No se comunica con OSE / SUNAT | El comprobante nunca se valida (sin CDR) | SPEC-007, SPEC-008 |
| No controla correlativos | Duplicados o saltos de numeración | SPEC-005 |
| Datos históricos informales | Pérdida de trazabilidad (RS 234-2006) | SPEC-009, SPEC-010 |

## 2. Alcance de esta fase (esqueleto Spec-First)

**Dentro del alcance**

- Comprobantes con contrato detallado: Factura (01), Boleta (03), Nota de Crédito (07), Nota de Débito (08).
- Comprobantes con caso de uso y endpoint, sin esquema detallado: Resumen Diario (RC), Comunicación de Baja (RA).
- Validaciones clave: RUC (módulo 11), DNI, series y correlativos, IGV 18 %, ISC (catálogo 08), ICBPER, cuadre de totales.
- Migración del legado de almacén.
- Arquitectura MVC monolítica preparada para Hexagonal / microservicios.

**Fuera del alcance (fase 2 o posterior)**

- Guía de Remisión Electrónica (DespatchAdvice) — se lista como caso de uso.
- Retenciones (20), Percepciones (40), detracciones con cuenta del Banco de la Nación, anticipos, exportación.
- Catálogo completo de reglas de validación SUNAT (códigos de error 2xxx / 3xxx / 4xxx uno por uno).
- Implementación (código).

## 3. Base normativa

| Norma | Qué exige | Impacto en el diseño |
|---|---|---|
| **RS N° 097-2012/SUNAT** | Crea el Sistema de Emisión Electrónica desarrollado desde los sistemas del contribuyente (SEE – Del Contribuyente). | El sistema genera, firma y envía el XML. Obliga a SPEC-006/007. |
| **RS N° 234-2006/SUNAT** | Normas sobre libros y registros vinculados a asuntos tributarios. | Registros formales, inalterables y trazables → auditoría y migración con origen (SPEC-009). |
| Normativa de masificación y modificatorias | Obligatoriedad de emisión electrónica y plazos de envío. | Plazos parametrizables (SPEC-007, SPEC-008). |
| **Anexo 8 — Catálogos SUNAT** | Códigos oficiales: tipo de documento, moneda, tributos, afectación IGV, ISC, etc. | SPEC-011 y `specs/catalogos/`. |
| **OASIS UBL 2.1** (`UBL-Invoice-2.1.xsd`, `UBL-CreditNote-2.1.xsd`, `UBL-DebitNote-2.1.xsd`) | Estructura XML del comprobante. | SPEC-006 y matriz de trazabilidad. |
| Guías de elaboración de XML UBL 2.1 de SUNAT | Personalización peruana de UBL (`CustomizationID = 2.0`, atributos `PE:SUNAT`). | Matriz de trazabilidad. |

> **Por qué el catálogo 08 es "punto clave":** ABC vende abarrotes, y en ese rubro hay
> productos afectos al **ISC**: cervezas y licores, cigarrillos (monto fijo), gaseosas y bebidas
> azucaradas (sistema al valor). El catálogo 08 define **cómo** se calcula el ISC
> (01 al valor, 02 monto fijo, 03 precio de venta al público) y el ISC **forma parte de la base del IGV**.
> Un error aquí arrastra error en IGV y en el total.

> Nota: los valores numéricos vigentes (tasa IGV 18 %, ICBPER S/ 0.50 por bolsa, umbral de
> S/ 700 en boletas, plazos de envío) se modelan como **parámetros con vigencia** y no como
> constantes, porque cambian por norma.

## 4. Glosario

| Término | Definición |
|---|---|
| **CPE** | Comprobante de Pago Electrónico. |
| **UBL** | Universal Business Language (OASIS), estándar XML del comprobante. |
| **OSE** | Operador de Servicios Electrónicos: valida el CPE por cuenta de SUNAT. |
| **CDR** | Constancia de Recepción: respuesta de SUNAT/OSE (aceptado, observado o rechazado). |
| **Serie / correlativo** | Identificador del CPE: `F001-00000001`. |
| **Valor de venta** | Monto sin impuestos. |
| **Precio de venta** | Monto con impuestos. |
| **RC / RA** | Resumen diario de boletas / Comunicación de baja. |
| **Legado** | Sistema actual de fichas de almacén. |
