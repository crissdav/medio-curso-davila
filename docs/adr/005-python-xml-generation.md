# ADR-005: UBL XML generation in Python with classes generated from the XSD

- **Status:** Accepted (replaces the backend language and XML library of ADR-001 for this component)
- **Date:** 2026-11-04

## Context

The second phase implements the XML generation from `UBL-Invoice-2.1.xsd`. ADR-001 proposed Kotlin with JAXB, but
that was a recommendation subject to the team's confirmation, and the team chose Python. The decisive requirement
does not change: **the XML must be built from classes generated from the XSD, not from text templates**.

## Decision

| Need | Choice |
|---|---|
| Language | Python 3.10+ |
| Classes from the XSD | `xsdata` generates `adapters/ubl/generated.py` from the official XSDs |
| Serialization | `xsdata` `XmlSerializer` |
| XSD validation before signing | `lxml` against `specs/ubl/xsd/` (SPEC-006 R-04) |
| Exact amounts | `decimal.Decimal`, never `float` (INV-10) |
| Tests | `pytest` |

The official runtime XSDs (`xsdrt`) and the generated module are versioned, so a fresh clone runs the tests without
downloading anything. To regenerate the module, with the virtual environment active (`xsdata` formats its output with
`ruff`, installed with `xsdata[cli]`, and it reformats the whole `adapters/ubl/` folder), from `src/`:

```bash
xsdata generate ../specs/ubl/xsd/maindoc/UBL-Invoice-2.1.xsd --package abc_invoicing.adapters.ubl.generated --structure-style single-package --docstring-style Blank
```

The ports-and-adapters design of ADR-002 is kept: `domain` imports neither `xsdata` nor `lxml`, and the generator is an
adapter behind `UblGeneratorPort`.

## Consequences

- (+) The XSD decides the element order and types: the generator cannot produce them in the wrong order.
- (+) Fast to write and to test; a clone only needs `pip install`.
- (+) Replacing the language later only touches this adapter: the contracts in `specs/` stay valid.
- (−) Generated code is large (about 38,000 lines) and takes a few seconds to import.
- (−) ADR-001 mentions a JVM backend. The language of the rest of the backend (signing, submission, API) must be
  confirmed before implementing it: XMLDSig in Python would use a library such as `signxml`.

## Alternatives considered

- **Java or Kotlin with JAXB**: the option proposed by ADR-001, more verbose to set up for this phase.
- **Text templates (Jinja2, Greenter's Twig approach)**: fast, but the structure is not tied to the XSD.
- **`lxml` building nodes by hand**: no generated classes, so element order and names depend on the programmer.
