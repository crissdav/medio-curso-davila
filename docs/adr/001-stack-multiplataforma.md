# ADR-001: Stack tecnológico multiplataforma

- **Estado:** Propuesto (recomendación justificada; sujeto a confirmación del equipo)
- **Fecha:** 2026-10-22

## Contexto

- El software debe correr **de forma nativa en Windows y en Android**.
- Debe distribuirse como **instalador MSI** (Windows) y **APK** (Android).
- Debe partir como **monolito MVC** y migrar a Hexagonal / microservicios.
- El dominio fiscal (UBL 2.1, firma XMLDSig, SOAP de SUNAT) necesita librerías maduras.

## Decisión

| Capa | Tecnología |
|---|---|
| Backend (monolito) | **Kotlin + Spring Boot 3** (JVM 21), Spring MVC, PostgreSQL |
| XML UBL | JAXB generado desde los XSD oficiales de OASIS UBL 2.1 |
| Firma | Apache Santuario (XMLDSig) con certificado `.pfx` |
| Envío SUNAT / OSE | Cliente SOAP (JAX-WS / Spring WS) |
| Clientes | **Kotlin Multiplatform + Compose Multiplatform** |
| Empaquetado Windows | `packageMsi` de Compose Desktop (jpackage + WiX) |
| Empaquetado Android | Gradle `assembleRelease` → APK firmado |

## Justificación

1. **Un solo lenguaje (Kotlin)** en backend y clientes: el módulo `shared/commonMain` contiene
   DTOs y validaciones de formato (RUC módulo 11, patrones de serie) **una sola vez** para Windows
   y Android.
2. **MSI y APK de serie**: Compose Multiplatform genera MSI con `packageMsi` y Android genera APK
   sin herramientas extra. Otras opciones necesitan trabajo adicional (ver alternativas).
3. **Ecosistema JVM para facturación**: JAXB, Santuario y JAX-WS son el camino que siguen las
   implementaciones de referencia del UBL peruano.
4. **Hexagonal natural**: los módulos Gradle permiten un módulo `domain` **sin dependencias**,
   con reglas de dependencia verificables (ArchUnit).

## Consecuencias

- (+) Reutilización de código cliente entre Windows y Android.
- (+) Spring MVC encaja directamente con el requisito "monolito MVC".
- (−) El MSI incluye un runtime JVM (instalador de ~80–120 MB).
- (−) El equipo debe conocer Kotlin.

## Alternativas consideradas

| Alternativa | Motivo de descarte |
|---|---|
| .NET MAUI | Windows se publica como MSIX, no MSI; generar MSI requiere WiX por separado. |
| Flutter | Windows genera `.exe` + carpeta; el MSI requiere tooling externo. Firma XML en Dart poco madura. |
| Tauri 2 (Rust + web) | Genera MSI y APK, pero la firma XMLDSig y JAXB-equivalentes en Rust son inmaduros. |
| Electron | No es nativo en Android. |
