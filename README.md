# ABC Software Corp — SUNAT Electronic Invoicing

Specifications and XML generator for the electronic invoicing system of ABC Software Corp, a Peruvian grocery
wholesaler and retailer. The project follows **Spec-First**: rules, contracts and traceability were defined first, and
the code then implements them.

**Reference country: Peru** — UBL 2.1 with the SUNAT customization.

| Phase | Deliverable | Status |
|---|---|---|
| Midterm exam | Specifications: domain model, architecture, API contracts and traceability matrix | Done, with the instructor's feedback applied |
| Second partial | Generation of the XML from the `UBL-Invoice-2.1.xsd` schema, with unit tests | Done |
| Signature | XMLDSig signature with a .pfx certificate (SPEC-006 R-05) | Done |
| Web form | Local form that calculates taxes and generates the signed XML | Done |
| Later | Submission to SUNAT/OSE, API and client apps | Specified, not implemented |

## Quick start

Requires Python 3.10 or later (tested on 3.13). The official XSDs and the generated classes are included, so nothing else is downloaded.

```bash
python -m venv .venv
.venv\Scripts\activate          # Linux / macOS: source .venv/bin/activate
pip install -e ".[dev]"

python -m pytest                # 101 tests: XML generation, signature, file name and web form
python -m abc_invoicing.web     # web form at http://127.0.0.1:8000
```

## Web form

A small local web app to issue a document without writing JSON: fill in the form, press **Generar XML** and download
the signed XML, ready to validate in Nubefact or another OSE.

```bash
python -m abc_invoicing.web                      # opens http://127.0.0.1:8000 in the browser
python -m abc_invoicing.web --port 8080 --no-browser
```

| Section | What is filled in |
|---|---|
| 1. Comprobante | Type (01 invoice, 03 sales receipt), series, number, issue date and time, currency; issuer data |
| 2. Cliente | Document type (RUC, DNI, foreigner ID, passport, or *Varios*), number, name, address. Each type shows its rule (RUC 11 digits with check digit, DNI 8 digits, foreigner ID and passport up to 12 characters) and the field checks it while typing |
| 3. Productos | Code, description, unit (catalog 03), quantity, **unit value without IGV**, IGV affectation (taxed, exempt, unaffected), and the **Bolsa ICBPER** box on plastic bag lines |
| 4. Forma de pago | Cash, or credit with installments (empty amounts are split equally) |

- **Taxes are calculated by the system** (SPEC-003): sale value, IGV, ICBPER, unit price with IGV, totals and the
  amount in words. The summary updates while typing.
- **Generar XML** builds the document, validates it against the XSD, signs it and returns it in ISO-8859-1 with the
  SUNAT file name (`20123456786-01-F001-00000125.xml`). Errors (an invoice without a valid RUC, a B series on an
  invoice, empty lines) are shown with their reason.
- **Descargar XML** saves the exact bytes. Load that file in Nubefact by drag and drop; copying the text or pressing
  BeautifyXML breaks the signature.
- The next number is suggested per series. *Cargar ejemplo* fills a sample invoice (also `http://127.0.0.1:8000/#ejemplo`).
- It signs with `certificado-prueba.pfx` (password `123456`), and creates that test certificate if it does not exist.
  `--cert` and `--password` (or `ABC_CERT_PASSWORD`) choose another one. The server only listens on `127.0.0.1`.
- Plastic bags go on their own line with **Bolsa ICBPER** checked: the bag count is the quantity, as SUNAT requires
  (error 3236 when `cbc:BaseUnitMeasure` differs from `cbc:InvoicedQuantity`).
- Not in the form yet: ISC, discounts and free-of-charge lines. They still work through the JSON input below.

To generate, sign and test an XML from a JSON file, see the next section.

## How to generate an XML

The generator turns a JSON document into a UBL 2.1 XML, validates it against the official XSD, signs it and writes it
in **ISO-8859-1**, the encoding SUNAT requires.

```text
input.json + company.json → generator → XSD check → XMLDSig signature (.pfx) → XML in ISO-8859-1
```

### 1. Create the test certificate (once)

```bash
python -m abc_invoicing.adapters.signature.test_certificate -o certificado-prueba.pfx --password 123456
```

It is self-signed and has **no legal value**; it is valid for one year. Real documents need a certificate from an
INDECOPI-accredited provider. `.pfx` and `.p12` files are in `.gitignore`: a private key must never be committed.

### 2. Write the input JSON

Copy [invoice-response.json](specs/schemas/examples/invoice-response.json) (invoice) or
[test_xml/02-B001-1/input.json](test_xml/02-B001-1/input.json) (sales receipt) and change the data. The generator does
not calculate taxes: the amounts must already be calculated and must add up, or the domain rejects the document.

| Field | Values |
|---|---|
| `documentType` / `series` | `01` invoice with an `F` series (`F001`); `03` sales receipt with a `B` series (`B001`) |
| `customer.documentType` | `6` RUC (required on invoices, check digit validated), `1` DNI, `-` anonymous (receipts below S/ 700) |
| `items[].igvAffectation` | `10` taxed, `20` exempt, `30` unaffected, `11`–`16`, `21`, `31`–`37` free of charge (catalog 07) |
| `items[].unitOfMeasure` | Catalog 03, such as `NIU` (unit) or `KGM` (kilogram) |
| `items[].isc` | Optional: `system` `01` (`rate`), `02` (`fixedAmount`, `unitConversionFactor`) or `03` (catalog 08) |
| `items[].icbperBagCount` | Number of plastic bags (S/ 0.50 each) |
| `paymentTerms.type` | `Contado` (cash) or `Credito` (credit, with installments) |
| `totals` | `taxedTotal + exemptTotal + unaffectedTotal = saleValueTotal`; `saleValueTotal + taxTotal − discountTotal = payableAmount` |

The company data (RUC, legal name, address) comes from [company.json](tests/fixtures/company.json).

### 3. Generate and sign

```bash
python -m abc_invoicing <input.json> tests/fixtures/company.json -d <folder> --cert certificado-prueba.pfx --password 123456
```

With `-d` the file is written in that folder with the **name SUNAT requires** (SPEC-006 R-08):

```text
{RUC}-{TYPE}-{SERIES}-{NUMBER}.xml      number padded with zeros to 8 digits
20123456786-01-F001-00000123.xml        invoice F001-123
20123456786-03-B001-00000001.xml        sales receipt B001-1
R-20123456786-01-F001-00000123.xml      CDR returned by SUNAT/OSE for that invoice
```

`-o <file>` writes to any name instead, for quick tests only. Without `--cert` the XML is not signed, and SUNAT and the OSE reject it with error 0306 (`ext:ExtensionContent` is
empty). The password can also be passed in the `ABC_CERT_PASSWORD` variable. If the package is not installed, prefix
the command with `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH="src";`).

### 4. Save it as a test and verify it

Each submission is kept in its own folder in [test_xml/](test_xml/): `NN-SERIES-NUMBER/` with `input.json`,
the signed XML and the CDR returned by the OSE or SUNAT, both with the SUNAT file name, and a `README.md` with the
result.

```bash
python -m abc_invoicing test_xml/02-B001-1/input.json tests/fixtures/company.json -d test_xml/02-B001-1 --cert certificado-prueba.pfx --password 123456
python test_xml/verify.py --cert certificado-prueba.pfx --password 123456
```

[verify.py](test_xml/verify.py) checks every test folder: ISO-8859-1 encoding, XSD, the project signature on
each invoice and the OSE/SUNAT signature on each CDR, and that each invoice has its SUNAT file name. Changing any signed
value makes it fail.

### 5. Send it to the OSE-DEMO

The XML can be tested at [probar-xml.nubefact.com](https://probar-xml.nubefact.com):

1. Choose **OSE** and press **Clean**.
2. Leave **Firmar** unchecked to test the project signature, or check it so Nubefact signs with its demo certificate.
3. **Drag the file** from the file explorer. Do not copy it from VS Code: VS Code opens it as UTF-8, shows `�`
   instead of `á`, and pasting sends the damaged text. To copy, first reopen it with *Reopen with Encoding → Western
   (ISO 8859-1)*.
4. Do not press **BeautifyXML**: changing the whitespace breaks the signature.
5. Press **ENVIAR** and save the response, converted to ISO-8859-1, as the CDR of the test.

| CDR `ResponseCode` | Meaning |
|---|---|
| `0` | Accepted; any `StatusReasonCode` of 4000 or more is an observation, not a rejection |
| `2000`–`3999` | Rejected; `Description` gives the reason |
| `0100`–`1999` | Not processed (format or system error); the document can be sent again |

| Error seen | Cause | Fix |
|---|---|---|
| 0306 `ExtensionContent` is not complete | Unsigned XML | Generate with `--cert`, or check **Firmar** |
| 2992 no tax rate tag on the line | Missing `cbc:Percent` | Already fixed in the generator (ISC system 02) |
| `JAXB unmarshalling exception` | Damaged characters (pasted from VS Code) | Drag the file instead |
| 4013 customer RUC not active | Example RUC not in the SUNAT register | Observation only; use a real active RUC |

## 1. The problem

ABC only has a warehouse system that records `fecha, ingreso, salida, producto, nro_documento`. It does not validate
RUCs, does not calculate taxes, does not generate UBL XML, is not signed and does not communicate with an OSE or SUNAT,
and it does not keep the formal records that SUNAT requires. The new system had to close those gaps, migrate the legacy
data without losing traceability, start as an MVC monolith ready for Hexagonal and microservices, and run on Windows
(MSI) and Android (APK).

## 2. What was done and why

### Specifications

| What | Why | Where |
|---|---|---|
| 13 functional specs with rules and acceptance criteria | Each one answers a gap in the case, so that every rule can be tested before code exists | [specs/features/](specs/features/) |
| Domain model with invariants and lifecycle | The rules live in the domain, not in the screens or the database | [02-domain-model](docs/02-domain-model.md) |
| JSON Schemas as contracts; amounts as decimal strings | `double` values cause rounding errors, a frequent reason for SUNAT rejections | [specs/schemas/](specs/schemas/) |
| 11 SUNAT catalogs, with the English description and the official name | Codes must come from one source, and legal wording must stay faithful to SUNAT | [specs/catalogs/](specs/catalogs/) |
| OpenAPI contract with 29 operations | The API is agreed before implementing it; the same contract survives the move to microservices | [openapi.yaml](specs/api/openapi.yaml), [04-api-contracts](docs/04-api-contracts.md) |
| Traceability matrix: 60 UBL rows, plus 35 rows for format 14.1 and 19 for format 12.1 | Every piece of data required by SUNAT can be followed from the regulation to the XML and the contract | [05-traceability-matrix](docs/05-traceability-matrix.md) |
| Use cases checked against Nubefact's public documentation | They reflect what real invoicing software does | [01-use-cases](docs/01-use-cases.md) |
| Legacy migration with one hash per row and reconciliation | Every record can be traced back to its source (RS 234-2006) | [06-legacy-migration](docs/06-legacy-migration.md) |

### Key decisions

| Decision | Why | Record |
|---|---|---|
| **MVC on the outside, ports and adapters on the inside** | The MVC model is a domain core with no framework, so moving to Hexagonal means reorganizing, not rewriting | [ADR-002](docs/adr/002-mvc-monolith-with-ports.md) |
| **Signing only on the server** | A lost phone must not expose the company's private key | [ADR-003](docs/adr/003-server-side-signing.md) |
| **Two transactions and an outbox** | The series lock lasts milliseconds and never waits for the OSE | [ADR-004](docs/adr/004-transactions-and-outbox.md) |
| **Kotlin Multiplatform for the clients** | It builds both the MSI and the APK from shared code | [ADR-001](docs/adr/001-multiplatform-stack.md) |
| **Python and `xsdata` for the XML** | The classes come from the official XSD, so the structure cannot drift from it; templates would allow that | [ADR-005](docs/adr/005-python-xml-generation.md) |

### Changes after the instructor's feedback

| Finding | Change | Why |
|---|---|---|
| Formats 14.1 and 12.1 were missing | [SPEC-013](specs/features/013-electronic-books-ple.md), [PLE tables](specs/ple-tables/), inventory fields, endpoints, [TXT samples](specs/ref/ple/) and matrix sections 11–12 | RS 234-2006 requires formal records, and an Excel report is not one. PLE units follow table 6, not UN/ECE, and exits in format 12.1 are negative |
| Incomplete HTTP codes | Reusable 401, 403, 429 and 5xx responses; 400 for format and 422 for business rules | A SUNAT rejection is not an API error: the document exists and its number is consumed, so it returns 201 with status `REJECTED` |
| Series lock tied to the OSE response | Numbering and submission are separated | A slow OSE would otherwise block every sale on that series |
| A note inherited from an invoice | Abstract `SalesDocument` | In UBL, `Invoice`, `CreditNote` and `DebitNote` are separate roots |
| Beer ISC "per litre" invoiced per unit | `unitConversionFactor` | A 620 ml bottle pays for 0.62 L, which changes the example total to S/ 377.67 |
| Row T-44 disagreed with the schema | `unitPrice` carries the reference value; `unitValue` is 0 on free-of-charge lines | The matrix and the contract must name the same field |
| Validator failed with Windows line endings | Line endings are normalized, and `.gitattributes` was added | The result must not depend on the operating system |

### XML generation (second partial)

```text
invoice-response.json → invoice_mapper → Invoice (domain) → UblInvoiceGenerator → classes from the XSD → XML → XSD check
```

| What | Why |
|---|---|
| [`generated.py`](src/abc_invoicing/adapters/ubl/generated.py) is generated by `xsdata` from `UBL-Invoice-2.1.xsd` | Element names, order and types come from the official schema |
| [`domain/`](src/abc_invoicing/domain/models.py) has no XML dependency and enforces invariants: F/B series, RUC check digit, sequence range and totals that add up | The XSD does not check these values, so an invalid document must stop before reaching the generator |
| [`invoice_generator.py`](src/abc_invoicing/adapters/ubl/invoice_generator.py) applies the SUNAT customization, citing the `T-nn` matrix row of each block | The code can be audited against the regulation |
| Every XML is validated against the XSD before it is returned | SPEC-006 R-04: a document that breaks the schema must never reach signing |

It generates invoices (01) and sales receipts (03) with taxed, exempt, unaffected and free-of-charge lines, ISC by catalog 08
system, ICBPER, line discounts, cash or credit payment terms and foreign currency.

The 116 tests check that the generated XML equals the [reference invoice](specs/ref/20123456786-01-F001-123.xml)
element by element, complies with the XSD, reports each matrix row correctly and handles the other operations. They also
reject invalid documents and confirm that the code's tax tables match the SUNAT catalogs
([test_invoice_generation.py](tests/test_invoice_generation.py)), verify the signature
([test_xml_signature.py](tests/test_xml_signature.py)), and cover the tax calculation and the web form
([test_web_form.py](tests/test_web_form.py)).

## 3. How it is verified

```bash
python -m pytest        # XML generation
npm install
npm run validate        # schemas, examples, arithmetic, matrix, PLE books, API responses, links, XML content and OpenAPI lint
npm run check:xsd       # sample XML files against the official XSD (requires Java 11+)
npm run check:mermaid   # renders the diagrams (requires Chrome or Edge)
```

The specifications are checked too, because a wrong spec produces wrong code: **936** automatic checks cover them.
OASIS UBL 2.1 provides the structure and the SUNAT customization defines the values for Peru, so sample XML files are
validated against [both layers](specs/ref/README.md). The tests and checks were also confirmed by introducing errors on
purpose, to verify that they fail when they should.

## 4. Repository map

```text
src/abc_invoicing/       XML generator: domain, application (mapper, tax calculator), UBL and signature adapters, web form
tests/                   Unit tests of the XML generation and signature
test_xml/                Submissions to the OSE/SUNAT: input, signed XML, CDR and result per test; verify.py
docs/                    Context, use cases, domain, architecture, API, matrix, migration and ADRs
specs/features/          Functional specs (SPEC-001 … SPEC-013)
specs/schemas/           JSON Schemas and validated examples
specs/api/               OpenAPI contract
specs/catalogs/          SUNAT catalogs of the XML
specs/ple-tables/        PLE tables and unit mapping for the books
specs/ubl/xsd/           Official OASIS UBL 2.1 XSDs (runtime version, unmodified)
specs/ref/               Sample XML and PLE files
scripts/                 Validators of the specifications
```

Start with [00-context](docs/00-context.md), which also has a glossary of the Peruvian tax terms.

**Exam deliverables:** [domain model and contracts](docs/02-domain-model.md) · [MVC architecture with a Hexagonal outlook](docs/03-architecture.md) · [API contracts](docs/04-api-contracts.md) · [traceability matrix](docs/05-traceability-matrix.md).

**Language:** the repository is in English. Official tax terms (RUC, IGV, ISC, ICBPER, CDR) and literal SUNAT values
(`FormaPago`, `Contado`, `Credito`) keep their original form, as do the legacy column names and the example business data.

## 5. Limitations and next steps

- **Not implemented:** credit and debit notes, tax calculation (the generator receives calculated
  amounts), IVAP and exports (rejected with an error), submission to SUNAT/OSE, the API and the client apps. The signature works, but a real tax document needs a certificate from an INDECOPI-accredited provider; the test certificate has no legal value.
- **Backend language:** ADR-001 proposed a JVM backend and ADR-005 implemented this component in Python. The language of
  the rest of the backend must be confirmed before implementing it.
- **To confirm against current regulations:** submission and voiding deadlines, the S/ 700 threshold, the S/ 0.50 ICBPER
  amount, the PLE file name and the table 13 codes. The ISC rates in the example are illustrative.
- **To validate with an accountant:** how credit notes, free-of-charge operations and rejected documents appear in format 14.1 (open questions in SPEC-013).
- **Pending by agreement:** separating the CDR ranges 0100–0999 and 1000–1999, and adding sample XML files for the sales receipt and the credit note.
- **Optional:** a walkthrough with a Nubefact DEMO account, which requires a RUC. The use cases were checked against its public documentation instead.
