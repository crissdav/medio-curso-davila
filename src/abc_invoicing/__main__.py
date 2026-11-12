"""Generates the XML of an invoice, signed when a certificate is given.

python -m abc_invoicing <invoice.json> <company.json> [-o out.xml] [--cert cert.pfx --password ****]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters.signature.xml_signer import XmlSigner, digest_value
from .adapters.ubl.invoice_generator import UblInvoiceGenerator
from .application.invoice_mapper import CompanyProfile, invoice_from_dto


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a UBL 2.1 invoice with the SUNAT customization.")
    parser.add_argument("invoice", type=Path, help="Invoice DTO (see specs/schemas/examples/invoice-response.json)")
    parser.add_argument("company", type=Path, help="Company profile (see tests/fixtures/company.json)")
    parser.add_argument("-o", "--output", type=Path, help="Output file; standard output if omitted")
    parser.add_argument("--cert", type=Path, help="Certificate .pfx/.p12 to sign with; unsigned XML if omitted")
    parser.add_argument("--password", help="Certificate password (or the ABC_CERT_PASSWORD variable)")
    args = parser.parse_args()

    dto = json.loads(args.invoice.read_text(encoding="utf-8"))
    company = CompanyProfile.from_dict(json.loads(args.company.read_text(encoding="utf-8")))
    xml = UblInvoiceGenerator().generate(invoice_from_dto(dto, company))
    if args.cert:
        password = args.password or os.environ.get("ABC_CERT_PASSWORD")
        xml = XmlSigner.from_pkcs12(args.cert, password).sign(xml)
        print(f"Signed. DigestValue: {digest_value(xml)}", file=sys.stderr)
    if args.output:
        args.output.write_bytes(xml)
    else:
        sys.stdout.buffer.write(xml)


if __name__ == "__main__":
    main()
