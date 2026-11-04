"""Generates the XML of an invoice: python -m abc_invoicing <invoice.json> <company.json> [-o out.xml]"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .adapters.ubl.invoice_generator import UblInvoiceGenerator
from .application.invoice_mapper import CompanyProfile, invoice_from_dto


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a UBL 2.1 invoice with the SUNAT customization.")
    parser.add_argument("invoice", type=Path, help="Invoice DTO (see specs/schemas/examples/invoice-response.json)")
    parser.add_argument("company", type=Path, help="Company profile (see tests/fixtures/company.json)")
    parser.add_argument("-o", "--output", type=Path, help="Output file; standard output if omitted")
    args = parser.parse_args()

    dto = json.loads(args.invoice.read_text(encoding="utf-8"))
    company = CompanyProfile.from_dict(json.loads(args.company.read_text(encoding="utf-8")))
    xml = UblInvoiceGenerator().generate(invoice_from_dto(dto, company))
    if args.output:
        args.output.write_bytes(xml)
    else:
        sys.stdout.buffer.write(xml)


if __name__ == "__main__":
    main()
