# Test 02: sales receipt B001-1

| | |
|---|---|
| Document | **Sales receipt (03)** B001-1, issued 2026-11-12 09:30, total S/ 51.75, cash |
| Issuer → customer | RUC 20123456786 → **DNI** 45781236, MARÍA QUISPE RAMÍREZ |
| Signature | Project test certificate (RSA-SHA256) |
| Encoding | ISO-8859-1 |
| **Result** | Pending: send to the OSE |

## What it tests, compared with test 01

| | Test 01 (F001-123) | Test 02 (B001-1) |
|---|---|---|
| Document type | Invoice (01), F series | Sales receipt (03), B series |
| Customer | Company with RUC (schemeID 6), with address | Person with DNI (schemeID 1), no address |
| Taxes | IGV, ISC (systems 01 and 02), ICBPER | IGV, **exempt from IGV (20, tax 9997 EXO)**, ICBPER |
| Units | NIU | NIU and **KGM** (kilograms) |
| Accented characters | Tingo María, plástica | MARÍA QUISPE RAMÍREZ, Plátano, plástica |

## Lines

| # | Product | Qty | Unit value | IGV affectation | Sale value | IGV | ICBPER |
|---|---|---|---|---|---|---|---|
| 1 | Leche evaporada lata 400 g | 6 NIU | 3.50 | 10 taxed | 21.00 | 3.78 | |
| 2 | Aceite vegetal botella 1 L | 2 NIU | 8.00 | 10 taxed | 16.00 | 2.88 | |
| 3 | Plátano de seda (kg) | 3 KGM | 2.50 | 20 exempt | 7.50 | 0.00 | |
| 4 | Bolsa plástica | 1 NIU | 0.0847 | 10 taxed | 0.08 | 0.01 | 0.50 |

Taxed 37.08 + exempt 7.50 = 44.58 · IGV 6.67 (37.08 × 18 %) · ICBPER 0.50 · **total 51.75**.

## Files

- [input.json](input.json): input data, in the same format as `specs/schemas/examples/invoice-response.json`.
- [invoice.xml](invoice.xml): generated and signed XML.
- `cdr-ose.xml`: pending, the OSE response (saved in ISO-8859-1).

```bash
python -m abc_invoicing test_xml/02-B001-1/input.json tests/fixtures/company.json -o test_xml/02-B001-1/invoice.xml --cert certificado-prueba.pfx --password 123456
python test_xml/verify.py --cert certificado-prueba.pfx --password 123456
```

## Sending it

OSE destination, **"Firmar" unchecked** (to test the project's signature), load the file by **drag and drop**, do not press
BeautifyXML.
