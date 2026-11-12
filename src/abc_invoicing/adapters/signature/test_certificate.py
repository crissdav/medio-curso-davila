"""Self-signed certificate for tests and the SUNAT beta environment. It has NO legal value.

python -m abc_invoicing.adapters.signature.test_certificate -o certificado-prueba.pfx --password 123456
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import BestAvailableEncryption, NoEncryption, pkcs12
from cryptography.x509.oid import NameOID


def make_test_certificate(
    ruc: str = "20123456786",
    legal_name: str = "ABC SOFTWARE CORP S.A.C.",
    not_before: datetime | None = None,
    days: int = 365,
) -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name(
        [
            x509.NameAttribute(NameOID.COUNTRY_NAME, "PE"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, legal_name),
            x509.NameAttribute(NameOID.SERIAL_NUMBER, ruc),
            x509.NameAttribute(NameOID.COMMON_NAME, f"{legal_name} - PRUEBA"),
        ]
    )
    start = not_before or datetime.now(timezone.utc) - timedelta(minutes=5)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(start)
        .not_valid_after(start + timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=True, key_encipherment=False,
                data_encipherment=False, key_agreement=False, key_cert_sign=False,
                crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def to_pkcs12(key: rsa.RSAPrivateKey, cert: x509.Certificate, password: str | None) -> bytes:
    encryption = BestAvailableEncryption(password.encode()) if password else NoEncryption()
    return pkcs12.serialize_key_and_certificates(b"abc-test", key, cert, None, encryption)


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a self-signed test certificate (.pfx). No legal value.")
    parser.add_argument("-o", "--output", type=Path, default=Path("certificado-prueba.pfx"))
    parser.add_argument("--password", default="123456")
    parser.add_argument("--ruc", default="20123456786")
    parser.add_argument("--name", default="ABC SOFTWARE CORP S.A.C.")
    args = parser.parse_args()
    key, cert = make_test_certificate(args.ruc, args.name)
    args.output.write_bytes(to_pkcs12(key, cert, args.password))
    print(f"{args.output} created (valid until {cert.not_valid_after_utc:%Y-%m-%d}, password: {args.password})")


if __name__ == "__main__":
    main()
