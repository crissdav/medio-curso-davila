# ABC Software Corp — SUNAT Electronic Invoicing (Spec-First)

**First phase (Spec-First)**: technical specifications defined before writing any business logic.
It contains no implementation code.
**Reference country: Peru** — UBL 2.1 with the SUNAT customization.

> Language: everything is in English following common practice. Official Peruvian tax terms (RUC,
> IGV, ISC, ICBPER, CDR) and literal SUNAT values (`FormaPago`, `Contado`, `Credito`) keep their
> original form; catalogs carry the official Spanish name next to the English description; legacy
> column names and example business data stay as they are in the source. See the glossary in
> [00-context](docs/00-context.md).

## 1. Summary of the work

| Phase | Result |
|---|---|
| **Understand** | Case analysis: the legacy system is a warehouse control (`fecha, ingreso, salida, producto, nro_documento`) without RUC validation, tax calculation, UBL XML or SUNAT/OSE connection. Regulatory basis: RS 097-2012, RS 234-2006, RS 000193-2020 (payment terms), SUNAT catalogs (with emphasis on **catalog 08 — ISC**) and UBL 2.1 with the SUNAT customization. |
| **Plan** | 12 functional specs derived from each gap in the exam statement, 3 architecture decisions (ADR) and a `docs/` + `specs/` structure. |
| **Act** | The 4 exam deliverables + use cases (checked against Nubefact), legacy migration, 12 JSON Schemas, 11 catalogs, OpenAPI contract and a sample SUNAT UBL XML invoice. |
| **Validate** | Automatic script with 456 checks, OpenAPI lint, rendering of the 10 diagrams and two-layer XML validation: structure (official UBL 2.1 XSD) and SUNAT content (catalogs, RUC, arithmetic and cross-check with the JSON). It caught and fixed 2 calculation errors in the invoice example. |

**Key decisions**

- **MVC on the outside, hexagonal on the inside:** MVC lives only in the delivery layer; the model is
  a domain core with ports, so migrating to Hexagonal / microservices means reorganizing, not rewriting.
- **ISC (catalog 08):** calculated before the IGV because it is part of its base; the invoice example
  uses beer (fixed amount, 02) and a soft drink (ad valorem, 01).
- **Legacy:** migrated with a hash per row for traceability; `nro_documento` never becomes a SUNAT sequence number.
- **Amounts as decimal strings** to avoid floating-point rounding errors.
- **Recommended stack:** Kotlin Multiplatform (MSI + APK) and Spring Boot; digital signing on the server only.

## 2. Exam deliverables

| Deliverable | Where |
|---|---|
| 1. Domain Model and Contracts (DTOs / Schemas) | [docs/02-domain-model.md](docs/02-domain-model.md) · [specs/schemas/](specs/schemas/) · [specs/catalogs/](specs/catalogs/) |
| 2. MVC Architecture Diagrams with a Hexagonal outlook | [docs/03-architecture.md](docs/03-architecture.md) · [docs/adr/](docs/adr/) |
| 3. Endpoint / Service Specification | [docs/04-api-contracts.md](docs/04-api-contracts.md) · [specs/api/openapi.yaml](specs/api/openapi.yaml) |
| 4. Regulatory Traceability Matrix SUNAT ↔ UBL | [docs/05-traceability-matrix.md](docs/05-traceability-matrix.md) |

Supporting material: [context and regulations](docs/00-context.md) · [use cases](docs/01-use-cases.md) ·
[legacy migration](docs/06-legacy-migration.md) · [UBL reference](specs/ref/README.md).

## 3. Functional specs

| ID | Spec |
|---|---|
| [SPEC-001](specs/features/001-invoice-receipt-issuance.md) | Invoice and sales receipt issuance |
| [SPEC-002](specs/features/002-credit-debit-notes.md) | Credit and debit notes |
| [SPEC-003](specs/features/003-tax-calculation.md) | Tax calculation (IGV, ISC cat. 08, ICBPER) |
| [SPEC-004](specs/features/004-identity-validation.md) | RUC / DNI validation |
| [SPEC-005](specs/features/005-series-numbering.md) | Series and sequence numbers |
| [SPEC-006](specs/features/006-ubl-xml-signature.md) | UBL 2.1 XML and digital signature |
| [SPEC-007](specs/features/007-ose-sunat-submission.md) | Submission to the OSE / SUNAT and CDR |
| [SPEC-008](specs/features/008-daily-summary-voiding.md) | Daily summary and voiding communication |
| [SPEC-009](specs/features/009-legacy-migration.md) | Legacy data migration |
| [SPEC-010](specs/features/010-inventory.md) | Inventory integrated with sales |
| [SPEC-011](specs/features/011-sunat-catalogs.md) | SUNAT catalogs |
| [SPEC-012](specs/features/012-multiplatform-distribution.md) | MSI / APK distribution |

ADR: [001 Stack](docs/adr/001-multiplatform-stack.md) ·
[002 MVC monolith with ports](docs/adr/002-mvc-monolith-with-ports.md) ·
[003 Server-side signing](docs/adr/003-server-side-signing.md).

## 4. Validation

```bash
npm install
npm run validate        # schemas, examples, SPEC-003 arithmetic, matrix, links, SUNAT XML content and OpenAPI lint
npm run check:mermaid   # renders the diagrams (uses an installed Chrome/Edge or CHROME_PATH)
npm run check:xsd       # STRUCTURE layer: XML against the official OASIS UBL 2.1 XSD (requires JDK 11+)
npm run check:sunat     # CONTENT layer: SUNAT codes, RUC, arithmetic and XML ↔ JSON cross-check (included in validate)
```

OASIS UBL 2.1 provides the structure and the SUNAT customization defines the values for Peru; that is
why the XML files are validated against both layers (details in [specs/ref/](specs/ref/README.md)).

## 5. Future work

- Confirm against the current regulations the submission and voiding deadlines, the sales receipt threshold (S/ 700) and the ICBPER amount (S/ 0.50).
- Replace the illustrative ISC rates in the example with the current rates.
- Detail the daily summary and voiding communication (SPEC-008) and the full catalog of SUNAT errors.

## 6. Pending (optional)

- **Nubefact DEMO account:** screen-by-screen walkthrough of the use cases. It requires a RUC, which is
  not available; the instructor stated it is optional. All 16 verification points were already
  confirmed with Nubefact's public documentation (section 7 of [use cases](docs/01-use-cases.md)).
