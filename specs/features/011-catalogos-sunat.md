# SPEC-011: Catálogos SUNAT

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** Anexo 8 SUNAT · [specs/catalogos/](../catalogos/) · [catalogo.schema.json](../schemas/catalogo.schema.json)

## Resumen
Fuente única y versionada de los códigos oficiales SUNAT usados en validaciones, cálculo y XML.

## Catálogos incluidos en la fase 1
| N° | Nombre | Uso principal |
|---|---|---|
| 01 | Tipo de documento | Raíz UBL, prefijo de serie |
| 02 | Moneda (ISO 4217) | `currencyID` en todos los montos |
| 03 | Unidad de medida (UN/ECE Rec 20) | `unitCode` en cantidades |
| 05 | Tributos | `TaxScheme` (IGV 1000, ISC 2000, ICBPER 7152, EXO 9997…) |
| 06 | Documento de identidad | `schemeID` del cliente; validación SPEC-004 |
| 07 | Afectación del IGV | `TaxExemptionReasonCode` por línea |
| **08** | **Sistema de cálculo del ISC** | `TierRange` por línea; fórmula SPEC-003 R-02 |
| 09 | Tipo de nota de crédito | `DiscrepancyResponse/ResponseCode` |
| 10 | Tipo de nota de débito | `DiscrepancyResponse/ResponseCode` |
| 16 | Tipo de precio | `PricingReference/PriceTypeCode` |
| 51 | Tipo de operación | `InvoiceTypeCode/@listID` |

## Reglas
| ID | Regla |
|---|---|
| R-01 | Todo código usado en DTOs, cálculo o XML debe existir en su catálogo (validado en CI por `scripts/validate.mjs`). |
| R-02 | Los catálogos se versionan con vigencia (`vigenteDesde`, `vigenteHasta`) en la base de datos; los JSON del repositorio son la semilla inicial. |
| R-03 | Códigos con `fase: 2` existen pero se rechazan en la emisión de la fase 1. |
| R-04 | El catálogo 07 define qué tributo (catálogo 05) corresponde a cada afectación. |

## Criterios de aceptación
- **AC-1:** `GET /catalogos/08` devuelve los 3 sistemas de cálculo del ISC.
- **AC-2:** Dada una línea con afectación `99`, entonces 400.
- **AC-3:** Dada una emisión con tipo de operación `0200` en fase 1, entonces 400.
