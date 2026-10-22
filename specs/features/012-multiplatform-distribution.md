# SPEC-012: Multiplatform distribution (Windows MSI and Android APK)

- **Status:** Draft
- **Date:** 2026-10-22
- **Related:** UC-19 · ADR-001, ADR-003

## Summary
Package and distribute the client application natively on Windows (MSI installer) and Android
(APK), sharing as much code as possible.

## Requirements
| ID | Requirement |
|---|---|
| R-01 | Windows 10/11 x64: **MSI** installer built with `packageMsi` (Compose Desktop); includes the runtime, a Start menu shortcut and uninstall from "Apps". |
| R-02 | Android 8.0+ (API 26): **APK** signed (`assembleRelease`) with the company keystore. |
| R-03 | Shared code in `shared/commonMain`: DTOs (generated from `specs/schemas/`), HTTP client, format validations (RUC modulus 11), offline queue. |
| R-04 | UI with Compose Multiplatform; platform differences (thermal printer, scanner, camera) behind `expect/actual` interfaces. |
| R-05 | The app **does not contain** the digital certificate nor authoritative calculation logic (ADR-003, SPEC-001 R-07). |
| R-06 | Offline Android: the sale is stored encrypted in a local queue and issued on synchronization (UC-19). |
| R-07 | Shared semantic versioning; the MSI and the APK are built in the same CI pipeline. |
| R-08 | Updates: MSI with a fixed `upgradeUuid` so that the new version replaces the previous one. |

## Acceptance criteria
- **AC-1:** Given the CI pipeline, when `v1.0.0` is tagged, then `ABCInvoicing-1.0.0.msi` and `abc-invoicing-1.0.0.apk` are published.
- **AC-2:** Given MSI 1.0.1 installed over 1.0.0, then a single version remains installed.
- **AC-3:** Given an Android device without network, when I record a sale, then it is queued and issued when the connection returns, without duplicates (`Idempotency-Key`).
