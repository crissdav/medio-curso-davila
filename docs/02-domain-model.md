# 02 — Domain model and contracts

> Exam deliverable 1. The executable contracts are in [specs/schemas/](../specs/schemas/)
> (JSON Schema 2020-12) and the catalogs in [specs/catalogs/](../specs/catalogs/).

## 1. Bounded contexts

Each context will be a **module** of the monolith and, in the future, a microservice candidate.

| Context | Responsibility | Aggregates / entities | Specs |
|---|---|---|---|
| **Invoicing** | Issue and manage documents | `SalesDocument`, `Invoice`, `Note`, `DocumentLine`, `Series` | 001, 002, 005 |
| **Taxation** | Calculate IGV / ISC / ICBPER and totals | `TaxCalculator`, `TaxRule`, `TaxParameter` | 003 |
| **Identity** | Validate and look up customers | `Customer`, `IdentityDocument`, `Taxpayer` | 004 |
| **SUNAT integration** | UBL XML, signature, submission, CDR, summary, voiding | `ElectronicDocument`, `Submission`, `Cdr`, `Ticket` | 006, 007, 008 |
| **Inventory** | Products and warehouse movements | `Product`, `InventoryMovement` | 010 |
| **Migration** | Import the legacy data with traceability | `MigrationBatch`, `MigrationIssue` | 009 |
| **Ledgers** | Formal books: formats 14.1 and 12.1 | `LedgerPeriod`, `SalesRecordLine`, `InventoryRecordLine` | 013 |
| **Catalogs** (shared) | SUNAT codes and PLE tables with effective periods | `Catalog`, `CatalogCode`, `UnitMappingCatalog` | 011, 013 |

## 2. Domain class diagram

```mermaid
classDiagram
    direction LR

    class SalesDocument {
        <<abstract>>
        +UUID id
        +DocumentType type
        +DocumentNumber number
        +LocalDate issueDate
        +Currency currency
        +DocumentStatus status
        +Totals totals
        +String documentHash
        +issue()
        +markSigned(hash)
        +recordCdr(Cdr)
        +voidDocument()
    }
    class Invoice {
        <<AggregateRoot>>
        +OperationType operationType
        +PaymentTerms paymentTerms
    }
    class DocumentLine {
        <<Entity>>
        +int lineNumber
        +Quantity quantity
        +UnitOfMeasure unit
        +Money unitValue
        +IgvAffectation affectation
        +IscConfig isc
        +int icbperBags
        +LineAmounts amounts
    }
    class Note {
        <<AggregateRoot>>
        +NoteType noteType
        +String reason
        +DocumentNumber affectedDocument
    }
    class Series {
        <<AggregateRoot>>
        +DocumentType type
        +String code
        +String establishment
        +long lastSequenceNumber
        +nextSequenceNumber() long
    }
    class Customer {
        <<Entity>>
        +IdentityDocument document
        +String legalName
        +Address address
    }
    class IdentityDocument {
        <<ValueObject>>
        +IdentityDocumentType type
        +String number
        +isValid() bool
    }
    class Issuer {
        <<Entity>>
        +Ruc ruc
        +String legalName
        +Certificate certificate
    }
    class Product {
        <<AggregateRoot>>
        +String code
        +String description
        +UnitOfMeasure unit
        +ExistenceType existenceType
        +IgvAffectation affectation
        +IscConfig isc
        +bool icbperApplicable
        +DataOrigin origin
    }
    class IscConfig {
        <<ValueObject>>
        +IscSystem system_cat08
        +Rate rate
        +Money fixedAmount
        +Decimal unitConversionFactor
        +Money retailPrice
    }
    class Totals {
        <<ValueObject>>
        +Money taxed
        +Money exempt
        +Money unaffected
        +Money free
        +Money isc
        +Money igv
        +Money icbper
        +Money payableAmount
    }
    class Cdr {
        <<ValueObject>>
        +String responseCode
        +CdrResult result
        +List~String~ notes
    }
    class InventoryMovement {
        <<Entity>>
        +MovementType type
        +String establishmentCode
        +ExistenceType existenceType
        +UnitOfMeasure unit
        +InventoryOperationType operationType
        +Quantity quantity
        +SourceDocument sourceDocument
        +Quantity balanceAfter
        +DataOrigin origin
    }
    class LedgerPeriod {
        <<AggregateRoot>>
        +YearMonth period
        +PeriodStatus status
        +close()
    }
    class SalesRecordLine {
        <<ReadModel>>
        format 14.1
    }
    class InventoryRecordLine {
        <<ReadModel>>
        format 12.1
    }
    class DataOrigin {
        <<ValueObject>>
        +SourceSystem system
        +String migrationBatch
        +int sourceRow
        +String sourceHash
    }
    class MigrationBatch {
        <<AggregateRoot>>
        +String id
        +BatchStatus status
        +Reconciliation reconciliation
    }
    class TaxCalculator {
        <<DomainService>>
        +calculate(List~DocumentLine~) Totals
    }

    SalesDocument <|-- Invoice
    SalesDocument <|-- Note
    SalesDocument "1" *-- "1..*" DocumentLine
    SalesDocument --> Customer : buyer
    SalesDocument --> Issuer
    SalesDocument --> Series : numbered by
    SalesDocument *-- Totals
    SalesDocument o-- "0..1" Cdr
    Note --> SalesDocument : affects
    Customer *-- IdentityDocument
    DocumentLine --> Product
    Product *-- IscConfig
    DocumentLine *-- IscConfig
    Product *-- DataOrigin
    InventoryMovement --> Product
    InventoryMovement *-- DataOrigin
    InventoryMovement ..> SalesDocument : outbound by sale
    MigrationBatch "1" o-- "*" InventoryMovement
    TaxCalculator ..> DocumentLine
    TaxCalculator ..> Totals
    SalesRecordLine ..> SalesDocument : derived from
    InventoryRecordLine ..> InventoryMovement : derived from
    LedgerPeriod "1" o-- "*" SalesRecordLine
    LedgerPeriod "1" o-- "*" InventoryRecordLine
```

## 3. Document lifecycle

```mermaid
stateDiagram-v2
    [*] --> DRAFT : calculate / preview
    DRAFT --> SIGNED : sequence number assigned + XML signed
    SIGNED --> SUBMITTED : sent to SUNAT or the OSE
    SIGNED --> PENDING_SUBMISSION : no connection
    PENDING_SUBMISSION --> SUBMITTED : retry
    SUBMITTED --> ACCEPTED : CDR code 0
    SUBMITTED --> OBSERVED : CDR ≥ 4000
    SUBMITTED --> REJECTED : CDR 2000-3999
    SUBMITTED --> PENDING_SUBMISSION : exception 0100-1999
    ACCEPTED --> VOIDED : voiding communication / credit note 01
    OBSERVED --> VOIDED : voiding communication / credit note 01
    REJECTED --> [*]
    VOIDED --> [*]
```

## 4. Domain invariants (rules the model never allows to break)

| ID | Invariant | Aggregate |
|---|---|---|
| INV-01 | A document has at least one line. | Invoice |
| INV-02 | Invoice (01) ⇒ series starts with `F` and the customer has a valid RUC (type 6). | Invoice |
| INV-03 | Sales receipt (03) ⇒ series starts with `B`; if the amount exceeds the current threshold (S/ 700) the customer must be identified. | Invoice |
| INV-04 | `payableAmount = Σ saleValue + Σ ISC + Σ IGV + Σ ICBPER + charges − global discounts` (±1.00 rounding tolerance). | Invoice |
| INV-05 | The sequence number is unique per (RUC, type, series), consecutive and **never reused**, even if the document is rejected. | Series |
| INV-06 | An `ACCEPTED` document is immutable; it is only corrected with a note or voiding. | Invoice |
| INV-07 | Note ⇒ references an existing document from the same issuer with a compatible series prefix (F↔F, B↔B). | Note |
| INV-08 | ISC ⇒ the product declares its `system` (catalog 08) and the parameter that system requires. | Product / Line |
| INV-09 | All migrated data keeps its `DataOrigin` with the hash of the original row. | Movement / Product |
| INV-10 | Amounts are handled as exact decimals (`BigDecimal`), never `double`. | All |
| INV-11 | A free-of-charge line has `unitValue = 0` and a `referenceUnitValue`, reported as `unitPrice` with catalog 16 code 02. | Line |
| INV-12 | `balanceAfter` is the previous balance of the product and establishment plus or minus the movement quantity. | Movement |
| INV-13 | The books of a period are generated only after the period is closed, and a closed period is never changed: corrections go to a later period. | LedgerPeriod |

## 5. Contract index (DTOs / schemas)

| Contract | File | Usage |
|---|---|---|
| Common types (Amount, Ruc, Series, catalog enums) | [common.schema.json](../specs/schemas/common.schema.json) | Reused by all |
| `SalesDocument`, `Totals` | [sales-document.schema.json](../specs/schemas/sales-document.schema.json) | SPEC-001, 002 |
| `IssueInvoiceRequest`, `Invoice`, `PaymentTerms` | [invoice.schema.json](../specs/schemas/invoice.schema.json) | SPEC-001 |
| `LineRequest`, `CalculatedLine` | [line.schema.json](../specs/schemas/line.schema.json) | SPEC-001, 002, 003 |
| `NoteDTO`, `IssuedNote` | [note.schema.json](../specs/schemas/note.schema.json) | SPEC-002 |
| `CustomerDTO` | [customer.schema.json](../specs/schemas/customer.schema.json) | SPEC-004 |
| `CdrResponseDTO` | [cdr-response.schema.json](../specs/schemas/cdr-response.schema.json) | SPEC-007 |
| `VoidedDocumentsDTO` | [voided-documents.schema.json](../specs/schemas/voided-documents.schema.json) | SPEC-008 |
| `LegacyMovementDTO` (source) | [legacy-movement.schema.json](../specs/schemas/legacy-movement.schema.json) | SPEC-009 |
| `InventoryMovementDTO` (target) | [inventory-movement.schema.json](../specs/schemas/inventory-movement.schema.json) | SPEC-009, 010 |
| `ProductDTO`, `IscConfig` | [product.schema.json](../specs/schemas/product.schema.json) | SPEC-003, 010 |
| `SalesRecordLine`, `InventoryRecordLine`, `LedgerPeriodStatus` | [ledger.schema.json](../specs/schemas/ledger.schema.json) | SPEC-013 |
| `SunatCatalogDTO` (catalogs and PLE tables) | [catalog.schema.json](../specs/schemas/catalog.schema.json) | SPEC-011, 013 |
| `ErrorDTO` (problem+json) | [error.schema.json](../specs/schemas/error.schema.json) | Whole API |

Examples validated against the schemas: [specs/schemas/examples/](../specs/schemas/examples/).

### Contract design decisions

- **Amounts as decimal strings**: JSON `number` is parsed as `double` by many clients and causes
  rounding errors (e.g. `0.1 + 0.2`). It is a frequent cause of rejections due to IGV mismatches.
- **A note is not an invoice**: in UBL, `Invoice`, `CreditNote` and `DebitNote` are separate roots (the debit note even uses `RequestedMonetaryTotal`), so `Invoice` and `Note` extend an abstract `SalesDocument`.
- **Request ≠ response**: the client sends only the input data (`LineRequest`); the amounts are
  **always** calculated by the domain (`CalculatedLine`). The calculation is not duplicated on
  Windows and Android, and totals sent by the client are never trusted.
- **English names, explicit UBL mapping**: the DTO uses English identifiers following common
  practice; Peruvian tax terms (RUC, IGV, ISC, ICBPER) keep their official acronyms. The translation
  to UBL XPath lives in a single adapter and is documented in the
  [traceability matrix](05-traceability-matrix.md).
