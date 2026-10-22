# SPEC-012: Distribución multiplataforma (Windows MSI y Android APK)

- **Estado:** Draft
- **Fecha:** 2026-10-22
- **Relacionado:** UC-19 · ADR-001, ADR-003

## Resumen
Empaquetar y distribuir la aplicación cliente de forma nativa en Windows (instalador MSI) y
Android (APK), compartiendo el máximo de código.

## Requisitos
| ID | Requisito |
|---|---|
| R-01 | Windows 10/11 x64: instalador **MSI** generado con `packageMsi` (Compose Desktop); incluye runtime, acceso directo en menú Inicio y desinstalación desde "Aplicaciones". |
| R-02 | Android 8.0+ (API 26): **APK** firmado (`assembleRelease`) con el keystore de la empresa. |
| R-03 | Código compartido en `shared/commonMain`: DTOs (generados desde `specs/schemas/`), cliente HTTP, validaciones de formato (RUC módulo 11), cola offline. |
| R-04 | UI con Compose Multiplatform; diferencias de plataforma (impresora térmica, escáner, cámara) detrás de interfaces `expect/actual`. |
| R-05 | La app **no contiene** certificado digital ni lógica de cálculo autoritativa (ADR-003, SPEC-003 R-07). |
| R-06 | Android sin conexión: la venta se guarda cifrada en cola local y se emite al sincronizar (UC-19). |
| R-07 | Versionado semántico común; el MSI y el APK se generan en el mismo pipeline de CI. |
| R-08 | Actualizaciones: MSI con `upgradeUuid` fijo para que la nueva versión reemplace la anterior. |

## Criterios de aceptación
- **AC-1:** Dado el pipeline de CI, cuando se etiqueta `v1.0.0`, entonces se publican `ABCFacturacion-1.0.0.msi` y `abc-facturacion-1.0.0.apk`.
- **AC-2:** Dado el MSI 1.0.1 instalado sobre 1.0.0, entonces queda una sola versión instalada.
- **AC-3:** Dado un Android sin red, cuando registro una venta, entonces queda en cola y se emite al recuperar la conexión, sin duplicarse (`Idempotency-Key`).
