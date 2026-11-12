"""Enveloped XMLDSig signature of the UBL XML (SPEC-006 R-05, R-07; ADR-003).

The signature goes inside ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent, with the Id that
cac:Signature/cbc:ID announces (T-03). The XML must already be valid against the XSD (R-04).
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from lxml import etree
from signxml import (
    CanonicalizationMethod,
    DigestAlgorithm,
    SignatureMethod,
    XMLSigner,
    XMLVerifier,
)

DS_NS = "http://www.w3.org/2000/09/xmldsig#"
NS = {
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ds": DS_NS,
}
XML_ENCODING = "ISO-8859-1"  # SPEC-006 R-09
# Inclusive C14N 1.0, the canonicalization used in the SUNAT samples.
C14N = CanonicalizationMethod.CANONICAL_XML_1_0


class SigningConfigurationError(ValueError):
    """The certificate or the document cannot be used for signing (SPEC-006 AC-3)."""


class XmlSigner:
    """Implements XmlSignerPort with an RSA key and its X.509 certificate."""

    def __init__(self, private_key: rsa.RSAPrivateKey, certificate: x509.Certificate) -> None:
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise SigningConfigurationError("The certificate key must be RSA (SPEC-006 R-05).")
        self._key = private_key
        self._certificate = certificate

    @classmethod
    def from_pkcs12(cls, path: Path, password: str | None) -> "XmlSigner":
        """Load the company certificate from a .pfx / .p12 file."""
        try:
            key, cert, _ = pkcs12.load_key_and_certificates(
                path.read_bytes(), password.encode() if password else None
            )
        except ValueError as exc:
            raise SigningConfigurationError(
                f"Cannot open {path.name}: wrong password or invalid file."
            ) from exc
        if key is None or cert is None:
            raise SigningConfigurationError(f"{path.name} has no private key or certificate.")
        return cls(key, cert)

    def sign(self, xml: bytes, now: datetime | None = None) -> bytes:
        self._check_validity(now or datetime.now(timezone.utc))
        root = etree.fromstring(xml)
        signature_id = _signature_id(root)

        # signxml puts the signature where the placeholder is (ExtensionContent).
        contents = root.xpath("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent", namespaces=NS)
        empty = [c for c in contents if len(c) == 0]
        if not empty:
            raise SigningConfigurationError("The XML has no empty ext:ExtensionContent for the signature.")
        etree.SubElement(empty[0], f"{{{DS_NS}}}Signature", Id="placeholder")

        signed = XMLSigner(
            signature_algorithm=SignatureMethod.RSA_SHA256,
            digest_algorithm=DigestAlgorithm.SHA256,
            c14n_algorithm=C14N,
        ).sign(root, key=self._key, cert=[self._certificate])  # root without Id → Reference URI=""

        # The Id is outside the signed content (enveloped transform), so it can be set afterwards.
        signed.find(".//ds:Signature", NS).set("Id", signature_id)
        return _serialize(signed)

    def _check_validity(self, now: datetime) -> None:
        cert = self._certificate
        if now > cert.not_valid_after_utc:
            raise SigningConfigurationError(
                f"The certificate expired on {cert.not_valid_after_utc:%Y-%m-%d} (SPEC-006 AC-3)."
            )
        if now < cert.not_valid_before_utc:
            raise SigningConfigurationError(
                f"The certificate is not valid until {cert.not_valid_before_utc:%Y-%m-%d}."
            )


def digest_value(signed_xml: bytes) -> str:
    """DigestValue of the signature, stored as documentHash (SPEC-006 R-07)."""
    found = etree.fromstring(signed_xml).xpath("//ds:Signature//ds:DigestValue/text()", namespaces=NS)
    if len(found) != 1:
        raise ValueError("The XML is not signed.")
    return found[0]


def verify_signature(signed_xml: bytes, certificate: x509.Certificate) -> None:
    """Raise signxml.InvalidSignature / InvalidDigest if the XML was altered (SPEC-006 AC-2)."""
    XMLVerifier().verify(signed_xml, x509_cert=certificate)


def _signature_id(root: etree._Element) -> str:
    found = root.xpath("cac:Signature/cbc:ID/text()", namespaces=NS)
    if len(found) != 1:
        raise SigningConfigurationError("The XML has no cac:Signature/cbc:ID (T-03).")
    return found[0]


def _serialize(root: etree._Element) -> bytes:
    body = etree.tostring(root, encoding=XML_ENCODING, xml_declaration=False)
    return f'<?xml version="1.0" encoding="{XML_ENCODING}"?>\n'.encode("ascii") + body
