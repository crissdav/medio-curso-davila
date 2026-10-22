# ADR-001: Multiplatform technology stack

- **Status:** Proposed (justified recommendation; subject to team confirmation)
- **Date:** 2026-10-22

## Context

- The software must run **natively on Windows and Android**.
- It must be distributed as an **MSI installer** (Windows) and an **APK** (Android).
- It must start as an **MVC monolith** and migrate to Hexagonal / microservices.
- The tax domain (UBL 2.1, XMLDSig signing, SUNAT SOAP) needs mature libraries.

## Decision

| Layer | Technology |
|---|---|
| Backend (monolith) | **Kotlin + Spring Boot 3** (JVM 21), Spring MVC, PostgreSQL |
| UBL XML | JAXB generated from the official OASIS UBL 2.1 XSDs |
| Signing | Apache Santuario (XMLDSig) with a `.pfx` certificate |
| SUNAT / OSE submission | SOAP client (JAX-WS / Spring WS) |
| Clients | **Kotlin Multiplatform + Compose Multiplatform** |
| Windows packaging | Compose Desktop `packageMsi` (jpackage + WiX) |
| Android packaging | Gradle `assembleRelease` → signed APK |

## Rationale

1. **A single language (Kotlin)** for backend and clients: the `shared/commonMain` module holds
   DTOs and format validations (RUC modulus 11, series patterns) **once** for Windows and Android.
2. **MSI and APK out of the box**: Compose Multiplatform builds the MSI with `packageMsi` and Android
   builds the APK with no extra tooling. Other options need additional work (see alternatives).
3. **JVM ecosystem for invoicing**: JAXB, Santuario and JAX-WS are the path followed by the
   reference implementations of Peruvian UBL.
4. **Natural hexagonal design**: Gradle modules allow a `domain` module **without dependencies**,
   with verifiable dependency rules (ArchUnit).

## Consequences

- (+) Client code reuse between Windows and Android.
- (+) Spring MVC fits the "MVC monolith" requirement directly.
- (−) The MSI bundles a JVM runtime (~80–120 MB installer).
- (−) The team must know Kotlin.

## Alternatives considered

| Alternative | Reason for rejection |
|---|---|
| .NET MAUI | Windows ships as MSIX, not MSI; building an MSI requires WiX separately. |
| Flutter | Windows produces an `.exe` + folder; the MSI needs external tooling. XML signing in Dart is immature. |
| Tauri 2 (Rust + web) | Builds MSI and APK, but XMLDSig signing and JAXB equivalents in Rust are immature. |
| Electron | Not native on Android. |
