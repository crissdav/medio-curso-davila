# Test 03: invoice F001-124 (credit)

| | |
|---|---|
| Document | **Invoice (01)** F001-124, issued 2026-11-12 11:00, total S/ 971.14 |
| Issuer → customer | RUC 20123456786 → RUC 20609876540, DISTRIBUIDORA EL ÑANDÚ S.A.C. |
| Payment | **Credit** in 2 installments: S/ 485.57 on 2026-12-12 and S/ 485.57 on 2027-01-11 |
| File name | `20123456786-01-F001-00000124.xml` (SPEC-006 R-08) |
| Signature | Project test certificate (RSA-SHA256) |
| Encoding | ISO-8859-1 |
| **Result** | Pending: send to the OSE |

## What it tests

- The SUNAT file name generated with `-d`.
- Credit payment terms: `FormaPago` / `Credito` with the pending amount and `Cuota001`, `Cuota002` with due dates
  (matrix T-20 to T-22).
- Accented characters in the customer (Ñ, Ú, á, í) and `×` in a description, all inside ISO-8859-1.

## Lines

| # | Product | Qty | Unit value | Sale value | IGV 18 % |
|---|---|---|---|---|---|
| 1 | Azúcar rubia saco 50 kg | 4 | 120.00 | 480.00 | 86.40 |
| 2 | Fideo spaghetti paquete 500 g | 40 | 2.20 | 88.00 | 15.84 |
| 3 | Aceite vegetal caja 12 × 1 L | 3 | 85.00 | 255.00 | 45.90 |

Taxed 823.00 · IGV 148.14 · **total 971.14** = installments 485.57 + 485.57.

## Files

- [input.json](input.json): input data.
- [20123456786-01-F001-00000124.xml](20123456786-01-F001-00000124.xml): generated and signed XML.
- `R-20123456786-01-F001-00000124.xml`: pending, the CDR (saved in ISO-8859-1).

```bash
python -m abc_invoicing test_xml/03-F001-124/input.json tests/fixtures/company.json -d test_xml/03-F001-124 --cert certificado-prueba.pfx --password 123456
python test_xml/verify.py --cert certificado-prueba.pfx --password 123456
```

## Sending it

OSE destination, load the file by **drag and drop** (do not paste it), do not press BeautifyXML. The customer RUC is
example data, so observation 4013 (customer RUC not active) is expected.
