# 03 — Arquitectura: MVC hoy, Hexagonal mañana, microservicios después

> Entregable 2 del examen. Decisiones formales en [docs/adr/](adr/).

## 1. Principio rector

> **"MVC por fuera, puertos y adaptadores por dentro."**

La gerencia pide un **monolito MVC** hoy y una migración **fácil** a Hexagonal / microservicios
mañana. Para que esa migración sea barata, el MVC se aplica **solo en la capa de entrega**
(controladores y vistas). El "Modelo" del MVC **no es** una capa de entidades JPA acopladas a
la base de datos: es un **núcleo de dominio puro** que se comunica con el exterior solo a través de
**interfaces (puertos)**.

| Letra MVC | Dónde vive | Qué contiene | ¿Cambia al migrar a Hexagonal? |
|---|---|---|---|
| **V**ista | App Compose (Windows/Android) + JSON | Pantallas, PDF, representación impresa | No |
| **C**ontrolador | `adapters/in/web` | Controladores REST, mapeo DTO ↔ comando | No (se renombra a "adaptador de entrada") |
| **M**odelo | `domain` + `application` | Entidades, reglas, casos de uso, puertos | No |
| (infraestructura) | `adapters/out/*` | JPA, firma XML, cliente SOAP SUNAT/OSE, padrón RUC | No — ya son adaptadores |

Por eso la migración es **reorganizar, no reescribir**.

## 2. Vista de contexto (C4 – nivel 1)

```mermaid
flowchart TB
    vend([Vendedor / Cajero])
    cont([Contador])
    adm([Administrador])
    subgraph ABC[Sistema de Facturación ABC]
        app[Apps cliente<br/>Windows MSI · Android APK]
        api[Monolito Facturación<br/>Spring Boot · MVC]
    end
    sunat[(SUNAT<br/>billService SOAP)]
    ose[(OSE<br/>operador autorizado)]
    padron[(Padrón RUC)]
    legado[(Sistema legado<br/>fichas de almacén)]
    mail[(Servidor de correo)]

    vend --> app
    cont --> app
    adm --> app
    app -- HTTPS/JSON --> api
    api -- XML UBL firmado --> ose
    api -- XML UBL firmado --> sunat
    api -- consulta --> padron
    legado -- CSV / volcado --> api
    api -- PDF + XML --> mail
```

## 3. Vista de contenedores — monolito MVC (estado inicial)

```mermaid
flowchart LR
    subgraph Clientes["Clientes (Kotlin Multiplatform)"]
        win["Windows · Compose Desktop<br/>instalador MSI"]
        andr["Android · Compose<br/>APK"]
        shared["shared/commonMain<br/>DTOs + validaciones de formato<br/>+ cola offline"]
        win --- shared
        andr --- shared
    end

    subgraph Monolito["Monolito Spring Boot (un único desplegable)"]
        direction TB
        C["Controller<br/>REST /api/v1"]
        M["Model<br/>dominio + casos de uso"]
        R["Adaptadores de salida<br/>JPA · UBL · Firma · SUNAT/OSE · Padrón"]
        C --> M --> R
    end

    db[("PostgreSQL<br/>esquemas por módulo")]
    files[("Almacén de archivos<br/>XML · CDR · PDF")]

    shared -- HTTPS JSON --> C
    R --> db
    R --> files
```

## 4. Vista de componentes — capas internas con visión hexagonal

```mermaid
flowchart LR
    subgraph IN["Adaptadores de ENTRADA (MVC: Controller)"]
        rest["ComprobanteController<br/>NotaController<br/>MigracionController<br/>…"]
        sched["Planificador<br/>(resumen diario, reintentos)"]
    end

    subgraph CORE["NÚCLEO — sin dependencias de framework (MVC: Model)"]
        subgraph APP["application"]
            pin["Puertos de entrada<br/>EmitirComprobanteUseCase<br/>EmitirNotaUseCase<br/>CalcularTributosUseCase<br/>ValidarClienteUseCase<br/>EnviarResumenUseCase<br/>MigrarLegadoUseCase"]
            svc["Servicios de aplicación<br/>(orquestan, transaccionales)"]
            pout["Puertos de salida<br/>ComprobanteRepository<br/>SerieRepository<br/>ProductoRepository<br/>PadronRucPort<br/>GeneradorUblPort<br/>FirmaDigitalPort<br/>EnvioSunatPort<br/>AlmacenArchivosPort<br/>FuenteLegadoPort"]
        end
        subgraph DOM["domain"]
            ent["Comprobante · Nota · Serie<br/>Producto · Cliente · Movimiento"]
            ds["CalculadoraTributos<br/>ValidadorRuc"]
        end
        pin --> svc --> ent
        svc --> ds
        svc --> pout
    end

    subgraph OUT["Adaptadores de SALIDA"]
        jpa["JPA / PostgreSQL"]
        ubl["UBL 2.1 (JAXB)"]
        sig["XMLDSig (certificado .pfx)"]
        soap["Cliente SOAP<br/>SunatAdapter | OseAdapter"]
        pad["PadronRucAdapter"]
        fs["Archivos XML/CDR/PDF"]
        leg["LegacyCsvAdapter"]
    end

    rest --> pin
    sched --> pin
    pout -. implementado por .-> jpa
    pout -. implementado por .-> ubl
    pout -. implementado por .-> sig
    pout -. implementado por .-> soap
    pout -. implementado por .-> pad
    pout -. implementado por .-> fs
    pout -. implementado por .-> leg
```

**Regla de dependencias** (verificable con ArchUnit en la fase de implementación):

1. `domain` no depende de nada (ni Spring, ni JPA, ni JAXB).
2. `application` depende solo de `domain`.
3. `adapters` dependen de `application` y `domain`; **nunca al revés**.
4. Los módulos de contexto (`facturacion`, `tributacion`, `inventario`…) se comunican solo por
   sus puertos públicos o por **eventos de dominio** (`ComprobanteAceptado`, `ComprobanteAnulado`).

### Estructura de paquetes (monolito modular)

```
com.abc.facturacion
├── facturacion/            ← contexto
│   ├── domain/             Comprobante, Nota, Serie, eventos
│   ├── application/
│   │   ├── port/in/        EmitirComprobanteUseCase …
│   │   ├── port/out/       ComprobanteRepository, SerieRepository …
│   │   └── service/
│   └── adapters/
│       ├── in/web/         ComprobanteController (MVC)
│       └── out/persistence/
├── tributacion/            CalculadoraTributos (dominio puro, sin adaptadores de salida)
├── identidad/              ValidadorRuc, PadronRucPort
├── integracionsunat/       GeneradorUbl, FirmaDigital, EnvioSunat (SUNAT u OSE)
├── inventario/
├── migracion/
└── catalogos/
```

## 5. Secuencia: emitir factura

```mermaid
sequenceDiagram
    autonumber
    actor V as Vendedor
    participant UI as App (Win/Android)
    participant C as ComprobanteController
    participant UC as EmitirComprobanteService
    participant ID as ValidadorRuc / PadronRucPort
    participant T as CalculadoraTributos
    participant S as SerieRepository
    participant X as GeneradorUblPort + FirmaDigitalPort
    participant E as EnvioSunatPort (OSE/SUNAT)
    participant R as ComprobanteRepository
    participant EV as Eventos (Inventario)

    V->>UI: Registra venta
    UI->>C: POST /comprobantes (Idempotency-Key)
    C->>UC: emitir(comando)
    UC->>ID: validar(RUC)
    ID-->>UC: ACTIVO / HABIDO
    UC->>T: calcular(líneas)
    T-->>UC: líneas + totales
    UC->>S: siguienteCorrelativo(F001) [bloqueo]
    S-->>UC: 123
    UC->>X: generar XML UBL 2.1 + firmar
    X-->>UC: XML firmado + hash
    UC->>R: guardar (FIRMADO)
    UC->>E: enviar(zip)
    alt CDR recibido
        E-->>UC: CDR (0 / ≥4000 / 2xxx-3xxx)
        UC->>R: actualizar estado
        UC-)EV: ComprobanteAceptado
    else Sin conexión
        E-->>UC: timeout
        UC->>R: PENDIENTE_ENVIO
    end
    UC-->>C: Comprobante
    C-->>UI: 201 / 202
```

## 6. Ruta de migración a microservicios

```mermaid
flowchart LR
    subgraph F1["Fase 1 — Monolito MVC modular (hoy)"]
        m1["1 desplegable<br/>1 BD, esquemas por módulo<br/>eventos en memoria"]
    end
    subgraph F2["Fase 2 — Hexagonal explícito"]
        m2["Mismo desplegable<br/>módulos con API interna<br/>eventos vía outbox"]
    end
    subgraph F3["Fase 3 — Microservicios"]
        g["API Gateway"]
        s1["svc-facturacion"]
        s2["svc-tributacion"]
        s3["svc-integracion-sunat"]
        s4["svc-inventario"]
        s5["svc-identidad"]
        bus[["Broker de eventos"]]
        g --> s1 & s4 & s5
        s1 --> s2
        s1 -- ComprobanteFirmado --> bus
        bus --> s3
        bus --> s4
    end
    F1 --> F2 --> F3
```

| Paso | Qué se extrae primero | Por qué |
|---|---|---|
| 1 | **Integración SUNAT** | Mayor latencia y variabilidad (timeouts, colas); escala distinto. Ya está detrás de `EnvioSunatPort`. |
| 2 | **Tributación** | Lógica pura y sin estado; cambia por norma con frecuencia. |
| 3 | **Inventario** | Ya se comunica por eventos (`ComprobanteAceptado`). |
| 4 | **Facturación / Identidad** | Núcleo transaccional; se separa al final. |

**Lo que no cambia en ninguna fase:** los contratos de [openapi.yaml](../specs/api/openapi.yaml) y los
JSON Schemas. El API Gateway enruta los mismos paths a servicios distintos.

## 7. Atributos de calidad y tácticas

| Atributo | Táctica |
|---|---|
| Disponibilidad ante caída de SUNAT/OSE | Estado `PENDIENTE_ENVIO`, reintentos con backoff, cola persistente. |
| Integridad de la numeración | Bloqueo pesimista por serie + `Idempotency-Key`. |
| Seguridad del certificado | Firma solo en servidor (ADR-003); `.pfx` en almacén de secretos. |
| Mantenibilidad ante cambios normativos | Parámetros con vigencia (IGV, ICBPER, umbrales) y catálogos versionados (SPEC-011). |
| Portabilidad | Kotlin Multiplatform: un código para Windows y Android (ADR-001). |
| Trazabilidad / auditoría | `OrigenDato` + bitácora de cambios de estado (RS 234-2006). |
