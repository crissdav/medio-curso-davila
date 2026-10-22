# SPEC-003: Cálculo de tributos (IGV, ISC — catálogo 08, ICBPER) y totales

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-01, UC-02, UC-18 · Catálogos 05, 07, 08, 16 · INV-04, INV-08, INV-10

## Resumen
Servicio de dominio puro (`CalculadoraTributos`) que, a partir de las líneas de venta, calcula los
importes por línea y los totales del comprobante.

## Motivación
El sistema actual "no calcula correctamente los impuestos" y en abarrotes conviven productos
gravados, exonerados, con ISC y bolsas con ICBPER (ver [00-contexto](../../docs/00-contexto.md)).

## Parámetros (con vigencia, no constantes)
| Parámetro | Valor de referencia | Fuente |
|---|---|---|
| Tasa IGV (incl. IPM) | 0.18 | TUO Ley IGV e ISC |
| ICBPER por bolsa | S/ 0.50 | Ley 30884 (valor vigente desde 2023) |
| Tasas / montos ISC | Por producto | Apéndices III y IV TUO IGV e ISC |

## Reglas de cálculo (orden obligatorio)
| ID | Regla |
|---|---|
| R-01 | `valorVenta = round2(cantidad × valorUnitario − descuento)` |
| R-02 | **ISC según catálogo 08**: <br>• `01` al valor: `montoIsc = valorVenta × tasa` <br>• `02` monto fijo: `montoIsc = cantidad × montoFijo` <br>• `03` precio venta al público: `montoIsc = cantidad × (precioVentaPublico / (1 + tasaIGV)) × tasa` |
| R-03 | `baseIgv = valorVenta + montoIsc` (el ISC **forma parte** de la base del IGV). |
| R-04 | IGV según catálogo 07: códigos `10`/`17` → `igv = round2(baseIgv × tasaIGV)`; `20`, `30`, `40` → `igv = 0`. |
| R-05 | Si la línea tiene `isc`, debe traer el parámetro del sistema elegido (01 → tasa; 02 → montoFijo; 03 → tasa + precioVentaPublico). Si no: `ISC_CONFIGURACION_INCOMPLETA`. |
| R-06 | `icbper = cantidadBolsas × montoIcbperVigente` (no forma parte de la base del IGV). |
| R-07 | Operaciones gratuitas (afectación 11–16, 21, 31–37): `valorUnitario` es referencial; se informa con catálogo 16 código `02`; **no suman al importe total**; se acumulan en `totalGratuitas` (tributo 9996). |
| R-08 | `precioUnitario = (valorVenta + montoIsc + igv) / cantidad` (catálogo 16 código `01`). |
| R-09 | Totales: `totalGravadas = Σ valorVenta (afectación 10, 17)`; `totalExoneradas = Σ (20)`; `totalInafectas = Σ (30)`; `totalIgv = round2(Σ baseIgv gravadas × tasaIGV)`; `importeTotal = totalValorVenta + totalIsc + totalIgv + totalIcbper − descuentoGlobal`. La diferencia entre Σ IGV de líneas y el IGV global no debe exceder ±1.00; si excede → `TOTALES_DESCUADRADOS`. |
| R-10 | Precisión: cálculo en `BigDecimal`, redondeo HALF_UP a 2 decimales en importes y hasta 10 en unitarios. |

## Ejemplo de referencia (abarrotes)
Ver [factura-response.json](../schemas/examples/factura-response.json). Valores de tasa ISC
**ilustrativos**:

| Ítem | Cat. 08 | Valor venta | ISC | Base IGV | IGV | ICBPER |
|---|---|---|---|---|---|---|
| Arroz 5 kg × 10 | — | 200.00 | 0.00 | 200.00 | 36.00 | — |
| Cerveza × 12 | 02 (S/ 1.25 c/u) | 48.00 | 15.00 | 63.00 | 11.34 | — |
| Gaseosa 3 L × 6 | 01 (17 %) | 48.00 | 8.16 | 56.16 | 10.11 | — |
| Bolsa × 2 | — | 0.17 | 0.00 | 0.17 | 0.03 | 1.00 |
| **Total** | | **296.17** | **23.16** | **319.33** | **57.48** | **1.00** |

Importe total = 296.17 + 23.16 + 57.48 + 1.00 = **377.81**.

## Criterios de aceptación
- **AC-1:** Dado el ejemplo de referencia, cuando calculo, entonces obtengo exactamente los importes de la tabla.
- **AC-2:** Dada una línea con ISC sistema 02 sin `montoFijo`, entonces 400 `ISC_CONFIGURACION_INCOMPLETA`.
- **AC-3:** Dada una línea exonerada (20), entonces `igv = 0.00` y suma a `totalExoneradas`.
- **AC-4:** Dada una línea gratuita (15), entonces no suma al `importeTotal` y suma a `totalGratuitas`.
- **AC-5:** Dado un cambio de tasa ICBPER con vigencia futura, cuando emito con fecha anterior, entonces se aplica la tasa anterior.

## Contratos
- `POST /tributos/calculos` · [linea.schema.json](../schemas/linea.schema.json) · `Totales` en [comprobante.schema.json](../schemas/comprobante.schema.json)
