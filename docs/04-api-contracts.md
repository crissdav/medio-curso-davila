# 04 — Endpoint and service specification (API contracts)

> Exam deliverable 3. Executable contract: [specs/api/openapi.yaml](../specs/api/openapi.yaml)
> (OpenAPI 3.1, references the JSON Schemas in `specs/schemas/`).

## 1. Conventions

| Aspect | Rule |
|---|---|
| Base | `/api/v1` — version in the path |
| Format | UTF-8 JSON; amounts as decimal strings |
| Authentication | Bearer JWT (roles: SALES, ACCOUNTANT, ADMIN, WAREHOUSE) |
| Idempotency | `Idempotency-Key` mandatory on issuing operations (a retry never consumes two sequence numbers) |
| Errors | `application/problem+json` with a business `code` or `SUNAT-nnnn` |
| Pagination | `page`, `pageSize` (max. 200) |

## 2. Endpoints (MVC input adapters → input ports)

| Method and path | Use case (input port) | Role | Spec |
|---|---|---|---|
| `POST /invoices` | `IssueInvoiceUseCase` | SALES | 001 |
| `GET /invoices` | `FindInvoicesQuery` | ACCOUNTANT | 001 |
| `GET /invoices/{id}` | `FindInvoicesQuery` | SALES, ACCOUNTANT | 001 |
| `GET /invoices/{id}/xml` | `DownloadFileQuery` | ACCOUNTANT | 006 |
| `GET /invoices/{id}/cdr` | `DownloadFileQuery` | ACCOUNTANT | 007 |
| `GET /invoices/{id}/pdf` | `RenderPrintedRepresentationUseCase` | SALES | 001 |
| `POST /invoices/{id}/resubmissions` | `ResubmitInvoiceUseCase` | ACCOUNTANT, system | 007 |
| `POST /notes` | `IssueNoteUseCase` | ACCOUNTANT | 002 |
| `POST /taxes/calculations` | `CalculateTaxesUseCase` | SALES | 003 |
| `GET /taxpayers/{ruc}` | `FindTaxpayerUseCase` | SALES | 004 |
| `POST /identity-documents/validations` | `ValidateDocumentUseCase` | SALES | 004 |
| `GET/POST /series` | `ManageSeriesUseCase` | ADMIN | 005 |
| `POST /daily-summaries` | `SubmitDailySummaryUseCase` | system, ACCOUNTANT | 008 |
| `POST /voided-documents` | `SubmitVoidedDocumentsUseCase` | ACCOUNTANT | 008 |
| `GET /tickets/{ticket}` | `FindTicketUseCase` | system, ACCOUNTANT | 008 |
| `GET/POST /products` | `ManageProductsUseCase` | ADMIN | 010 |
| `GET/POST /inventory/movements` | `RecordMovementUseCase` | WAREHOUSE | 010 |
| `POST /migrations` | `MigrateLegacyUseCase` | ADMIN | 009 |
| `GET /migrations/{batch}` | `FindBatchQuery` | ADMIN | 009 |
| `GET /migrations/{batch}/issues` | `FindBatchQuery` | ADMIN | 009 |
| `GET /catalogs/{number}` | `FindCatalogQuery` | all | 011 |
| `GET /public/invoices` | `LookupPublicInvoiceQuery` (UC-24) | public, no token | 001 |
| `GET /reports/invoices` | `ExportReportQuery` (UC-15, UC-26) | ACCOUNTANT | 001 |

## 3. Output ports (internal service contracts)

Interfaces the core **requires** and the infrastructure implements. They are the contracts that
allow swapping SUNAT for an OSE, PostgreSQL for another database, or a local module for a microservice.

```kotlin
// application/port/out — reference signatures (not an implementation)

interface SeriesRepository {
    /** Atomically reserves the next sequence number (lock per series). INV-05 */
    fun nextSequenceNumber(ruc: Ruc, type: DocumentType, series: String): Long
}

interface InvoiceRepository {
    fun save(invoice: Invoice)
    fun findByNumber(ruc: Ruc, type: DocumentType, number: DocumentNumber): Invoice?
    fun findByIdempotencyKey(key: UUID): Invoice?
    fun pendingSubmission(limit: Int): List<Invoice>
}

interface RucRegistryPort {
    /** Status (ACTIVO, BAJA…) and condition (HABIDO, NO HABIDO). May answer from cache. */
    fun find(ruc: Ruc): Taxpayer?
}

interface UblGeneratorPort {
    /** Translates the aggregate into UBL 2.1 XML according to the traceability matrix. */
    fun generate(invoice: Invoice): XmlDocument
}

interface DigitalSignaturePort {
    /** Enveloped XMLDSig inside ext:UBLExtensions; returns the signed XML + DigestValue (hash). */
    fun sign(xml: XmlDocument): SignedXml
}

interface SunatSubmissionPort {   // implementations: SunatAdapter, OseAdapter
    fun submitDocument(zip: ZipFile): Cdr          // sendBill (synchronous)
    fun submitSummary(zip: ZipFile): Ticket        // sendSummary (asynchronous)
    fun getTicketStatus(ticket: Ticket): Cdr       // getStatus
}

interface FileStoragePort {
    fun save(path: String, content: ByteArray)
    fun read(path: String): ByteArray
}

interface LegacySourcePort {
    fun readRows(batch: MigrationBatch): Sequence<LegacyRow>
}

interface CatalogPort {
    fun effectiveCode(catalog: String, code: String, date: LocalDate): CatalogCode?
}
```

## 4. Contracts with external systems

| System | Protocol | Operations | Adapter |
|---|---|---|---|
| SUNAT SEE | SOAP (WS-Security with SOL user) | `sendBill`, `sendSummary`, `getStatus` | `SunatAdapter` |
| OSE | SUNAT-compatible SOAP (per operator) | same | `OseAdapter` |
| RUC registry | Reduced registry file (daily download) or external service | lookup by RUC | `RucRegistryAdapter` |
| Legacy | CSV / dump of the current database | batch read | `LegacyCsvAdapter` |

Submitted file: `{RUC}-{TYPE}-{SERIES}-{NUMBER}.zip` containing the XML with the same name
(e.g. `20123456786-01-F001-123.zip`).

## 5. Business error codes

| Code | HTTP | Rule |
|---|---|---|
| `INVALID_RUC` | 400 | SPEC-004 R-01 (modulus 11) |
| `CUSTOMER_NOT_LOCATED` | 400 / warning | SPEC-004 R-03 |
| `CUSTOMER_REQUIRED_FOR_RECEIPT` | 400 | SPEC-001 R-04 (S/ 700 threshold) |
| `SERIES_NOT_AUTHORIZED` | 400 | SPEC-005 R-02 |
| `SERIES_MISMATCH` | 400 | SPEC-002 R-02 |
| `ISC_CONFIG_INCOMPLETE` | 400 | SPEC-003 R-05 |
| `TOTALS_MISMATCH` | 400 | SPEC-003 R-09 |
| `DOCUMENT_IMMUTABLE` | 409 | INV-06 |
| `SUBMISSION_IN_PROGRESS` | 409 | SPEC-007 R-04 |
| `SUNAT-nnnn` | 422 | SUNAT/OSE rejection (2000-3999) |
