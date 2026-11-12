"""Checks every test in test_xml/: ISO-8859-1 encoding, XSD and valid signatures.

python test_xml/verify.py [--cert certificado-prueba.pfx --password 123456]

- {RUC}-{TYPE}-{SERIES}-{NUMBER}.xml (Invoice): SUNAT file name (SPEC-006 R-08), XSD and signature, verified
  against the project certificate when --cert is given, otherwise against the one embedded in the XML.
- R-{RUC}-...xml (CDR, ApplicationResponse): signature of the OSE/SUNAT, verified against the certificate
  embedded in the CDR.
"""
from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from signxml import XMLVerifier

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "src"))
from abc_invoicing.adapters.ubl.xsd_validator import validate_invoice  # noqa: E402

DS = {"ds": "http://www.w3.org/2000/09/xmldsig#"}
ENCODING = "ISO-8859-1"
INVOICE_NS = "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
CBC = "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"


def sunat_file_name(root: etree._Element) -> str:
    """Expected name from the XML content: {RUC}-{TYPE}-{SERIES}-{NUMBER:08}.xml."""
    ns = {"cbc": CBC, "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"}
    ruc = root.xpath("cac:AccountingSupplierParty/cac:Party/cac:PartyIdentification/cbc:ID/text()", namespaces=ns)[0]
    doc_type = root.xpath("cbc:InvoiceTypeCode/text()", namespaces=ns)[0]
    series, number = root.xpath("cbc:ID/text()", namespaces=ns)[0].split("-")
    return f"{ruc}-{doc_type}-{series}-{int(number):08d}.xml"


def embedded_certificate(data: bytes) -> x509.Certificate:
    b64 = etree.fromstring(data).xpath("//ds:X509Certificate/text()", namespaces=DS)
    if not b64:
        raise ValueError("no ds:X509Certificate (the XML is not signed)")
    return x509.load_der_x509_certificate(base64.b64decode("".join(b64[0].split())))


def check(path: Path, own_cert: x509.Certificate | None) -> list[str]:
    data = path.read_bytes()
    errors = []
    root = etree.fromstring(data)
    is_invoice = root.tag == f"{{{INVOICE_NS}}}Invoice"
    encoding = root.getroottree().docinfo.encoding
    if encoding.upper() != ENCODING:
        errors.append(f"encoding {encoding}, expected {ENCODING}")
    if is_invoice:
        if path.name != sunat_file_name(root):
            errors.append(f"file name should be {sunat_file_name(root)} (SPEC-006 R-08)")
        try:
            validate_invoice(data)
        except ValueError as exc:
            errors.append(f"XSD: {exc}")
    try:
        cert = own_cert if (own_cert and is_invoice) else embedded_certificate(data)
        XMLVerifier().verify(data, x509_cert=cert)
        signer = cert.subject.get_attributes_for_oid(x509.NameOID.ORGANIZATION_NAME)
        print(f"    signature OK ({signer[0].value if signer else cert.subject.rfc4514_string()})")
    except Exception as exc:  # noqa: BLE001 - every failure is reported
        errors.append(f"signature: {type(exc).__name__}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cert", type=Path, help="Project certificate (.pfx) that must have signed the invoices")
    parser.add_argument("--password")
    args = parser.parse_args()
    own = None
    if args.cert:
        _, own, _ = pkcs12.load_key_and_certificates(
            args.cert.read_bytes(), args.password.encode() if args.password else None
        )

    failed = 0
    for test in sorted(p for p in ROOT.iterdir() if p.is_dir() and not p.name.startswith(("_", "."))):
        print(test.name)
        for xml in sorted(test.glob("*.xml")):
            print(f"  {xml.name}")
            for error in check(xml, own):
                print(f"    FAIL {error}")
                failed += 1
    print("\nAll checks passed." if not failed else f"\n{failed} check(s) failed.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
