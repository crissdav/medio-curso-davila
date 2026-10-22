# 03 — Architecture: MVC today, Hexagonal tomorrow, microservices later

> Exam deliverable 2. Formal decisions in [docs/adr/](adr/).

## 1. Guiding principle

> **"MVC on the outside, ports and adapters on the inside."**

Management asks for an **MVC monolith** today and an **easy** migration to Hexagonal / microservices
tomorrow. To keep that migration cheap, MVC applies **only to the delivery layer** (controllers and
views). The MVC "Model" is **not** a layer of JPA entities coupled to the database: it is a **pure
domain core** that talks to the outside world only through **interfaces (ports)**.

| MVC letter | Where it lives | What it contains | Does it change when moving to Hexagonal? |
|---|---|---|---|
| **V**iew | Compose app (Windows/Android) + JSON | Screens, PDF, printed representation | No |
| **C**ontroller | `adapters/in/web` | REST controllers, DTO ↔ command mapping | No (renamed to "input adapter") |
| **M**odel | `domain` + `application` | Entities, rules, use cases, ports | No |
| (infrastructure) | `adapters/out/*` | JPA, XML signing, SUNAT/OSE SOAP client, RUC registry | No — they already are adapters |

That is why the migration means **reorganizing, not rewriting**.

## 2. Context view (C4 – level 1)

```mermaid
flowchart TB
    sales([Salesperson / Cashier])
    acc([Accountant])
    adm([Administrator])
    subgraph ABC[ABC Invoicing System]
        app[Client apps<br/>Windows MSI · Android APK]
        api[Invoicing monolith<br/>Spring Boot · MVC]
    end
    sunat[(SUNAT<br/>billService SOAP)]
    ose[(OSE<br/>authorized operator)]
    registry[(RUC registry)]
    legacy[(Legacy system<br/>warehouse records)]
    mail[(Mail server)]

    sales --> app
    acc --> app
    adm --> app
    app -- HTTPS/JSON --> api
    api -- signed UBL XML --> ose
    api -- signed UBL XML --> sunat
    api -- lookup --> registry
    legacy -- CSV / dump --> api
    api -- PDF + XML --> mail
```

## 3. Container view — MVC monolith (initial state)

```mermaid
flowchart LR
    subgraph Clients["Clients (Kotlin Multiplatform)"]
        win["Windows · Compose Desktop<br/>MSI installer"]
        andr["Android · Compose<br/>APK"]
        shared["shared/commonMain<br/>DTOs + format validations<br/>+ offline queue"]
        win --- shared
        andr --- shared
    end

    subgraph Monolith["Spring Boot monolith (single deployable)"]
        direction TB
        C["Controller<br/>REST /api/v1"]
        M["Model<br/>domain + use cases"]
        R["Output adapters<br/>JPA · UBL · Signature · SUNAT/OSE · Registry"]
        C --> M --> R
    end

    db[("PostgreSQL<br/>schema per module")]
    files[("File storage<br/>XML · CDR · PDF")]

    shared -- HTTPS JSON --> C
    R --> db
    R --> files
```

## 4. Component view — internal layers with a hexagonal outlook

```mermaid
flowchart LR
    subgraph IN["INPUT adapters (MVC: Controller)"]
        rest["InvoiceController<br/>NoteController<br/>MigrationController<br/>…"]
        sched["Scheduler<br/>(daily summary, retries)"]
    end

    subgraph CORE["CORE — no framework dependencies (MVC: Model)"]
        subgraph APP["application"]
            pin["Input ports<br/>IssueInvoiceUseCase<br/>IssueNoteUseCase<br/>CalculateTaxesUseCase<br/>ValidateCustomerUseCase<br/>SubmitSummaryUseCase<br/>MigrateLegacyUseCase"]
            svc["Application services<br/>(orchestration, transactional)"]
            pout["Output ports<br/>InvoiceRepository<br/>SeriesRepository<br/>ProductRepository<br/>RucRegistryPort<br/>UblGeneratorPort<br/>DigitalSignaturePort<br/>SunatSubmissionPort<br/>FileStoragePort<br/>LegacySourcePort"]
        end
        subgraph DOM["domain"]
            ent["Invoice · Note · Series<br/>Product · Customer · Movement"]
            ds["TaxCalculator<br/>RucValidator"]
        end
        pin --> svc --> ent
        svc --> ds
        svc --> pout
    end

    subgraph OUT["OUTPUT adapters"]
        jpa["JPA / PostgreSQL"]
        ubl["UBL 2.1 (JAXB)"]
        sig["XMLDSig (.pfx certificate)"]
        soap["SOAP client<br/>SunatAdapter | OseAdapter"]
        reg["RucRegistryAdapter"]
        fs["XML/CDR/PDF files"]
        leg["LegacyCsvAdapter"]
    end

    rest --> pin
    sched --> pin
    pout -. implemented by .-> jpa
    pout -. implemented by .-> ubl
    pout -. implemented by .-> sig
    pout -. implemented by .-> soap
    pout -. implemented by .-> reg
    pout -. implemented by .-> fs
    pout -. implemented by .-> leg
```

**Dependency rule** (verifiable with ArchUnit during implementation):

1. `domain` depends on nothing (no Spring, no JPA, no JAXB).
2. `application` depends only on `domain`.
3. `adapters` depend on `application` and `domain`; **never the other way around**.
4. Context modules (`invoicing`, `taxation`, `inventory`…) communicate only through their public
   ports or through **domain events** (`InvoiceAccepted`, `InvoiceVoided`).

### Package structure (modular monolith)

```
com.abc.invoicing
├── invoicing/              ← context
│   ├── domain/             Invoice, Note, Series, events
│   ├── application/
│   │   ├── port/in/        IssueInvoiceUseCase …
│   │   ├── port/out/       InvoiceRepository, SeriesRepository …
│   │   └── service/
│   └── adapters/
│       ├── in/web/         InvoiceController (MVC)
│       └── out/persistence/
├── taxation/               TaxCalculator (pure domain, no output adapters)
├── identity/               RucValidator, RucRegistryPort
├── sunatintegration/       UblGenerator, DigitalSignature, SunatSubmission (SUNAT or OSE)
├── inventory/
├── migration/
└── catalogs/
```

## 5. Sequence: issue an invoice

```mermaid
sequenceDiagram
    autonumber
    actor V as Salesperson
    participant UI as App (Win/Android)
    participant C as InvoiceController
    participant UC as IssueInvoiceService
    participant ID as RucValidator / RucRegistryPort
    participant T as TaxCalculator
    participant S as SeriesRepository
    participant X as UblGeneratorPort + DigitalSignaturePort
    participant E as SunatSubmissionPort (OSE/SUNAT)
    participant R as InvoiceRepository
    participant EV as Events (Inventory)

    V->>UI: Records a sale
    UI->>C: POST /invoices (Idempotency-Key)
    C->>UC: issue(command)
    UC->>ID: validate(RUC)
    ID-->>UC: ACTIVE / LOCATED
    UC->>T: calculate(lines)
    T-->>UC: lines + totals
    UC->>S: nextSequenceNumber(F001) [lock]
    S-->>UC: 123
    UC->>X: build UBL 2.1 XML + sign
    X-->>UC: signed XML + hash
    UC->>R: save (SIGNED)
    UC->>E: submit(zip)
    alt CDR received
        E-->>UC: CDR (0 / ≥4000 / 2xxx-3xxx)
        UC->>R: update status
        UC-)EV: InvoiceAccepted
    else No connection
        E-->>UC: timeout
        UC->>R: PENDING_SUBMISSION
    end
    UC-->>C: Invoice
    C-->>UI: 201 / 202
```

## 6. Migration path to microservices

```mermaid
flowchart LR
    subgraph F1["Phase 1 — Modular MVC monolith (today)"]
        m1["1 deployable<br/>1 DB, schema per module<br/>in-memory events"]
    end
    subgraph F2["Phase 2 — Explicit hexagonal"]
        m2["Same deployable<br/>modules with internal API<br/>events via outbox"]
    end
    subgraph F3["Phase 3 — Microservices"]
        g["API Gateway"]
        s1["svc-invoicing"]
        s2["svc-taxation"]
        s3["svc-sunat-integration"]
        s4["svc-inventory"]
        s5["svc-identity"]
        bus[["Event broker"]]
        g --> s1 & s4 & s5
        s1 --> s2
        s1 -- InvoiceSigned --> bus
        bus --> s3
        bus --> s4
    end
    F1 --> F2 --> F3
```

| Step | What is extracted first | Why |
|---|---|---|
| 1 | **SUNAT integration** | Highest latency and variability (timeouts, queues); scales differently. Already behind `SunatSubmissionPort`. |
| 2 | **Taxation** | Pure, stateless logic; changes often with regulations. |
| 3 | **Inventory** | Already communicates through events (`InvoiceAccepted`). |
| 4 | **Invoicing / Identity** | Transactional core; split last. |

**What never changes in any phase:** the contracts in [openapi.yaml](../specs/api/openapi.yaml) and the
JSON Schemas. The API Gateway routes the same paths to different services.

## 7. Quality attributes and tactics

| Attribute | Tactic |
|---|---|
| Availability when SUNAT/OSE is down | `PENDING_SUBMISSION` status, retries with backoff, persistent queue. |
| Numbering integrity | Pessimistic lock per series + `Idempotency-Key`. |
| Certificate security | Signing on the server only (ADR-003); `.pfx` in a secrets store. |
| Maintainability under regulatory changes | Parameters with effective periods (IGV, ICBPER, thresholds) and versioned catalogs (SPEC-011). |
| Portability | Kotlin Multiplatform: one codebase for Windows and Android (ADR-001). |
| Traceability / audit | `DataOrigin` + status change log (RS 234-2006). |
