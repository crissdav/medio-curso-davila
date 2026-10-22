# 05 — Matriz de trazabilidad normativa (SUNAT ↔ UBL 2.1 ↔ DTO)

> Entregable 4 del examen. Cada fila cruza un **requisito de SUNAT** (dato exigido y su catálogo)
> con el **elemento UBL 2.1** (XPath relativo a la raíz `Invoice` / `CreditNote` / `DebitNote`),
> el **campo del contrato** (DTO) y la **spec** que lo valida.
>
> Esta tabla es verificada automáticamente por `scripts/validate.mjs`: toda ruta DTO debe existir
> en los JSON Schemas y todo código `cat-NN:código` debe existir en `specs/catalogos/`.

Prefijos: `cbc:` = CommonBasicComponents, `cac:` = CommonAggregateComponents,
`ext:` = CommonExtensionComponents, `ds:` = XMLDSig.

## 1. Cabecera del comprobante (Factura 01 / Boleta 03 — raíz `Invoice`)

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-01 | Versión UBL | — | `cbc:UBLVersionID` | valor fijo `2.1` | (constante) | 006 |
| T-02 | Versión de la estructura | — | `cbc:CustomizationID` | valor `2.0`; `schemeAgencyName="PE:SUNAT"` | (constante) | 006 |
| T-03 | Firma digital | — | `ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature` | XMLDSig enveloped | `Comprobante.hashCpe` | 006 |
| T-04 | Datos del firmante | — | `cac:Signature/cbc:ID`, `cac:Signature/cac:SignatoryParty` | ID de firma + RUC emisor | `Comprobante.emisor.ruc` | 006 |
| T-05 | Serie y número | — | `cbc:ID` | `F001-123` (sin ceros a la izquierda obligatorios) | `Comprobante.numero` | 005 |
| T-06 | Fecha de emisión | — | `cbc:IssueDate` | `aaaa-mm-dd` | `Comprobante.fechaEmision` | 001 |
| T-07 | Hora de emisión | — | `cbc:IssueTime` | `hh:mm:ss` | `Comprobante.horaEmision` | 001 |
| T-08 | Tipo de comprobante | `cat-01:01`, `cat-01:03` | `cbc:InvoiceTypeCode` | `listAgencyName="PE:SUNAT"`, `listName="Tipo de Documento"`, `listURI=…catalogo01` | `Comprobante.tipoComprobante` | 001 |
| T-09 | Tipo de operación | `cat-51:0101` | `cbc:InvoiceTypeCode/@listID` | `listID="0101"` | `Comprobante.tipoOperacion` | 001 |
| T-10 | Importe en letras | — (catálogo 52, leyenda 1000) | `cbc:Note` | `languageLocaleID="1000"` | `Comprobante.totales.importeEnLetras` | 001 |
| T-11 | Moneda | `cat-02:PEN`, `cat-02:USD` | `cbc:DocumentCurrencyCode` | `listID="ISO 4217 Alpha"`, `listAgencyName="United Nations Economic Commission for Europe"` | `Comprobante.moneda` | 001 |

## 2. Emisor y adquiriente

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-12 | RUC del emisor | `cat-06:6` | `cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID` | `schemeID="6"`, `schemeAgencyName="PE:SUNAT"`, `schemeURI=…catalogo06` | `Comprobante.emisor.ruc` | 004 |
| T-13 | Razón social del emisor | — | `cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | — | `Comprobante.emisor.razonSocial` | 001 |
| T-14 | Nombre comercial | — | `cac:AccountingSupplierParty/cac:Party/cac:PartyName/cbc:Name` | — | `Comprobante.emisor.nombreComercial` | 001 |
| T-15 | Código de establecimiento | — | `cac:AccountingSupplierParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:AddressTypeCode` | `0000` = domicilio fiscal | `Comprobante.emisor.establecimiento` | 005 |
| T-16 | Tipo de documento del adquiriente | `cat-06:6`, `cat-06:1`, `cat-06:-` | `cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID/@schemeID` | `schemeAgencyName="PE:SUNAT"` | `Comprobante.cliente.tipoDocumento` | 004 |
| T-17 | Número de documento del adquiriente | — | `cac:AccountingCustomerParty/cac:Party/cac:PartyIdentification/cbc:ID` | RUC módulo 11 / DNI 8 dígitos | `Comprobante.cliente.numeroDocumento` | 004 |
| T-18 | Nombre o razón social del adquiriente | — | `cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cbc:RegistrationName` | — | `Comprobante.cliente.razonSocial` | 001 |
| T-19 | Dirección del adquiriente | — | `cac:AccountingCustomerParty/cac:Party/cac:PartyLegalEntity/cac:RegistrationAddress/cac:AddressLine/cbc:Line` | — | `Comprobante.cliente.direccion` | 001 |

## 3. Forma de pago

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-20 | Forma de pago | — | `cac:PaymentTerms/cbc:PaymentMeansID` (con `cbc:ID` = `FormaPago`) | valores `Contado` / `Credito` | `Comprobante.formaPago.tipo` | 001 |
| T-21 | Monto neto pendiente de pago | — | `cac:PaymentTerms/cbc:Amount` | `currencyID` | `Comprobante.formaPago.montoPendiente` | 001 |
| T-22 | Cuotas (monto y vencimiento) | — | `cac:PaymentTerms/cbc:Amount`, `cac:PaymentTerms/cbc:PaymentDueDate` (con `cbc:PaymentMeansID` = `Cuota001`…) | `currencyID` | `Comprobante.formaPago.cuotas[].monto`, `Comprobante.formaPago.cuotas[].fechaVencimiento` | 001 |

## 4. Totales e impuestos del comprobante

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-23 | Monto total de impuestos | — | `cac:TaxTotal/cbc:TaxAmount` | `currencyID` | `Comprobante.totales.totalImpuestos` | 003 |
| T-24 | Total operaciones gravadas + IGV | `cat-05:1000` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount`, `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (TaxScheme 1000) | `cac:TaxScheme/cbc:ID`=1000, `cbc:Name`=IGV, `cbc:TaxTypeCode`=VAT | `Comprobante.totales.totalGravadas`, `Comprobante.totales.totalIgv` | 003 |
| T-25 | Total exoneradas | `cat-05:9997` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` (TaxScheme 9997) | `cbc:Name`=EXO, `cbc:TaxTypeCode`=VAT | `Comprobante.totales.totalExoneradas` | 003 |
| T-26 | Total inafectas | `cat-05:9998` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` (TaxScheme 9998) | `cbc:Name`=INA, `cbc:TaxTypeCode`=FRE | `Comprobante.totales.totalInafectas` | 003 |
| T-27 | Total gratuitas | `cat-05:9996` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount` (TaxScheme 9996) | `cbc:Name`=GRA, `cbc:TaxTypeCode`=FRE | `Comprobante.totales.totalGratuitas` | 003 |
| T-28 | Total ISC | `cat-05:2000` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (TaxScheme 2000) | `cbc:Name`=ISC, `cbc:TaxTypeCode`=EXC | `Comprobante.totales.totalIsc` | 003 |
| T-29 | Total ICBPER | `cat-05:7152` | `cac:TaxTotal/cac:TaxSubtotal/cbc:TaxAmount` (TaxScheme 7152) | `cbc:Name`=ICBPER, `cbc:TaxTypeCode`=OTH | `Comprobante.totales.totalIcbper` | 003 |
| T-30 | Total valor de venta | — | `cac:LegalMonetaryTotal/cbc:LineExtensionAmount` | `currencyID` | `Comprobante.totales.totalValorVenta` | 003 |
| T-31 | Total precio de venta | — | `cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount` | `currencyID` | `Comprobante.totales.totalPrecioVenta` | 003 |
| T-32 | Total descuentos | — | `cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount` | `currencyID` | `Comprobante.totales.totalDescuentos` | 003 |
| T-33 | Redondeo | — | `cac:LegalMonetaryTotal/cbc:PayableRoundingAmount` | `currencyID` | `Comprobante.totales.redondeo` | 003 |
| T-34 | Importe total | — | `cac:LegalMonetaryTotal/cbc:PayableAmount` | `currencyID` | `Comprobante.totales.importeTotal` | 003 |

## 5. Líneas (`cac:InvoiceLine`)

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-40 | Número de ítem | — | `cac:InvoiceLine/cbc:ID` | correlativo desde 1 | `Comprobante.items[].numeroLinea` | 001 |
| T-41 | Cantidad y unidad de medida | `cat-03:NIU`, `cat-03:ZZ` | `cac:InvoiceLine/cbc:InvoicedQuantity` | `unitCode`, `unitCodeListID="UN/ECE rec 20"` | `Comprobante.items[].cantidad`, `Comprobante.items[].unidadMedida` | 001 |
| T-42 | Valor de venta del ítem | — | `cac:InvoiceLine/cbc:LineExtensionAmount` | `currencyID` | `Comprobante.items[].valorVenta` | 003 |
| T-43 | Precio de venta unitario | `cat-16:01` | `cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount` + `cbc:PriceTypeCode` | `listName="Tipo de Precio"`, `listURI=…catalogo16` | `Comprobante.items[].precioUnitario` | 003 |
| T-44 | Valor referencial (gratuitas) | `cat-16:02` | `cac:InvoiceLine/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount` + `cbc:PriceTypeCode` | `PriceTypeCode=02` | `Comprobante.items[].valorUnitario` | 003 |
| T-45 | Valor unitario (sin impuestos) | — | `cac:InvoiceLine/cac:Price/cbc:PriceAmount` | `currencyID`; 0 en gratuitas | `Comprobante.items[].valorUnitario` | 003 |
| T-46 | Descripción | — | `cac:InvoiceLine/cac:Item/cbc:Description` | máx. 500 | `Comprobante.items[].descripcion` | 001 |
| T-47 | Código de producto del vendedor | — | `cac:InvoiceLine/cac:Item/cac:SellersItemIdentification/cbc:ID` | — | `Comprobante.items[].codigoProducto` | 010 |
| T-48 | Código de producto SUNAT | — (catálogo 25, UNSPSC) | `cac:InvoiceLine/cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode` | `listID="UNSPSC"`, `listAgencyName="GS1 US"` | `Producto.codigoProductoSunat` | 010 |
| T-49 | Afectación del IGV | `cat-07:10`, `cat-07:20`, `cat-07:30`, `cat-07:15` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TaxExemptionReasonCode` | `listAgencyName="PE:SUNAT"`, `listURI=…catalogo07` | `Comprobante.items[].afectacionIgv` | 003 |
| T-50 | Base, tasa y monto de IGV del ítem | `cat-05:1000` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount`, `cbc:TaxAmount`, `cac:TaxCategory/cbc:Percent` | `Percent`=18 | `Comprobante.items[].baseIgv`, `Comprobante.items[].igv`, `Comprobante.items[].tasaIgv` | 003 |
| **T-51** | **Sistema de cálculo del ISC** ★ | `cat-08:01`, `cat-08:02`, `cat-08:03` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:TierRange` (TaxScheme 2000) | `cbc:TierRange` = código catálogo 08 | `Comprobante.items[].isc.sistema` | 003 |
| T-52 | Base, tasa y monto de ISC del ítem | `cat-05:2000` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:TaxableAmount`, `cbc:TaxAmount`, `cac:TaxCategory/cbc:Percent` (TaxScheme 2000) | `cbc:Name`=ISC, `cbc:TaxTypeCode`=EXC | `Comprobante.items[].baseIsc`, `Comprobante.items[].montoIsc`, `Comprobante.items[].isc.tasa` | 003 |
| T-53 | ICBPER del ítem | `cat-05:7152` | `cac:InvoiceLine/cac:TaxTotal/cac:TaxSubtotal/cbc:BaseUnitMeasure`, `cac:TaxCategory/cbc:PerUnitAmount`, `cbc:TaxAmount` (TaxScheme 7152) | `BaseUnitMeasure/@unitCode="NIU"` | `Comprobante.items[].cantidadBolsasIcbper`, `Comprobante.items[].icbper` | 003 |
| T-54 | Descuento del ítem | — (catálogo 53, código 00) | `cac:InvoiceLine/cac:AllowanceCharge/cbc:Amount` (`cbc:ChargeIndicator`=false) | `cbc:AllowanceChargeReasonCode="00"` | `Comprobante.items[].descuento` | 003 |
| T-55 | Total tributos del ítem | — | `cac:InvoiceLine/cac:TaxTotal/cbc:TaxAmount` | `currencyID` | `Comprobante.items[].totalImpuestos` | 003 |

## 6. Notas de crédito (raíz `CreditNote`) y débito (raíz `DebitNote`)

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-60 | Tipo de nota | `cat-09:01`, `cat-09:07`, `cat-10:01` | `cac:DiscrepancyResponse/cbc:ResponseCode` | `listURI=…catalogo09` / `…catalogo10` | `Nota.tipoNota` | 002 |
| T-61 | Motivo o sustento | — | `cac:DiscrepancyResponse/cbc:Description` | — | `Nota.motivo` | 002 |
| T-62 | Comprobante afectado (serie-número) | — | `cac:BillingReference/cac:InvoiceDocumentReference/cbc:ID` | — | `Nota.documentoAfectado.numero` | 002 |
| T-63 | Tipo del comprobante afectado | `cat-01:01`, `cat-01:03` | `cac:BillingReference/cac:InvoiceDocumentReference/cbc:DocumentTypeCode` | `listURI=…catalogo01` | `Nota.documentoAfectado.tipoComprobante` | 002 |
| T-64 | Cantidad de la nota | `cat-03:NIU` | `cac:CreditNoteLine/cbc:CreditedQuantity` o `cac:DebitNoteLine/cbc:DebitedQuantity` | `unitCode` | `Nota.items[].cantidad` | 002 |
| T-65 | Tipo de documento de la nota | `cat-01:07`, `cat-01:08` | Raíz `CreditNote` o `DebitNote` | — | `Nota.tipoComprobante` | 002 |
| T-66 | Importe total (nota de débito) | — | `cac:RequestedMonetaryTotal/cbc:PayableAmount` | En `DebitNote` reemplaza a `LegalMonetaryTotal` | `Comprobante.totales.importeTotal` | 002 |

## 7. Respuesta (CDR — raíz `ApplicationResponse`)

| ID | Dato exigido por SUNAT | Catálogo | XPath UBL 2.1 | Atributos (personalización SUNAT) | Campo DTO | Spec |
|---|---|---|---|---|---|---|
| T-70 | Código de respuesta | — | `cac:DocumentResponse/cac:Response/cbc:ResponseCode` | 0 / 0100-1999 / 2000-3999 / ≥4000 | `Cdr.codigoRespuesta` | 007 |
| T-71 | Descripción de la respuesta | — | `cac:DocumentResponse/cac:Response/cbc:Description` | — | `Cdr.descripcion` | 007 |
| T-72 | Observaciones | — | `cbc:Note` | códigos ≥ 4000 | `Cdr.observaciones` | 007 |

## 8. Cruce con el sistema legado

| ID | Campo legado | Destino en el nuevo modelo | ¿Llega a un elemento UBL? | Regla |
|---|---|---|---|---|
| L-01 | `fecha` | `MovimientoInventario.fecha` | No (historia de almacén, no es CPE) | SPEC-009 M-02 |
| L-02 | `ingreso` | `MovimientoInventario.cantidad` (tipo INGRESO) | No | SPEC-009 M-03 |
| L-03 | `salida` | `MovimientoInventario.cantidad` (tipo SALIDA) | No | SPEC-009 M-03 |
| L-04 | `producto` | `Producto.descripcion` → en ventas nuevas: `cac:Item/cbc:Description` (T-46) | **Sí, indirectamente** (el producto migrado se usa en ventas nuevas) | SPEC-009 M-04 |
| L-05 | `nro_documento` | `MovimientoInventario.documentoReferencia.numero` | **No**: nunca se convierte en `cbc:ID` (T-05) | SPEC-009 M-05 · SPEC-005 R-07 |

## 9. Diferencias entre el ejemplo genérico de OASIS y la personalización SUNAT

Referencia: [UBL-Invoice-2.1-Example.xml](../specs/ref/README.md).

| Elemento | Ejemplo OASIS (genérico UE) | SUNAT (Perú) |
|---|---|---|
| `cbc:CustomizationID` | Ausente | Obligatorio `2.0` |
| `cbc:InvoiceTypeCode` | `380` (UN/ECE 1001) | `01` / `03` (catálogo 01) con `@listID` = tipo de operación |
| Identificación de las partes | `cbc:EndpointID schemeID="GLN"` | `cac:PartyIdentification/cbc:ID schemeID="6"` (catálogo 06) |
| Esquema del impuesto | `TaxScheme/ID = VAT` (UN/ECE 5153) | `TaxScheme/ID = 1000` (catálogo 05) + `Name` + `TaxTypeCode` |
| Categoría del impuesto | `TaxCategory/ID = S, AA, E` (UN/ECE 5305) | `TaxExemptionReasonCode` (catálogo 07) y `TierRange` para ISC (catálogo 08) |
| Moneda | `EUR` | `PEN` / `USD` |
| Precio con impuestos | No se informa | `cac:PricingReference` obligatorio (catálogo 16) |
| Firma | No incluida | `ext:UBLExtensions` + `cac:Signature` obligatorios |
| Forma de pago | `cac:PaymentMeans` (código UN/ECE 4461) | `cac:PaymentTerms` con `ID="FormaPago"` (Contado / Crédito / Cuota) |
| Leyendas | `cbc:Note` libre | `cbc:Note languageLocaleID` (catálogo 52) |

## 10. Cobertura

| Contrato | Campos con correspondencia UBL | Campos sin correspondencia (justificados) |
|---|---|---|
| `Comprobante` | Ver T-01 … T-55 | `id`, `estado`, `enlaces` (uso interno); `correlativo`, `serie` (incluidos en `numero`, T-05); `cdr` (ver T-70 … T-72); `cliente.ubigeo`, `cliente.correo` (envío al cliente); `items[].isc.montoFijo`, `items[].isc.precioVentaPublico` (parámetros de cálculo: se reflejan en el monto de T-52); `totales.totalExportacion` (fase 2, tributo 9995) |
| `Nota` | T-60 … T-66 | `serie`, `fechaEmision` y `moneda` siguen las mismas filas que en `Comprobante` (T-05, T-06, T-11) |
| `Cdr` | T-70 … T-72 | `resultado` (derivado), `canal`, `ticket`, `fechaRecepcion` |
