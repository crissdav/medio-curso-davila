"""SPEC-006 R-05, R-07, R-09, AC-2 and AC-3: enveloped XMLDSig signature."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from lxml import etree
from signxml import InvalidDigest, InvalidSignature

from abc_invoicing.adapters.signature.test_certificate import make_test_certificate, to_pkcs12
from abc_invoicing.adapters.signature.xml_signer import (
    SigningConfigurationError,
    XmlSigner,
    digest_value,
    verify_signature,
)
from abc_invoicing.adapters.ubl.xsd_validator import validate_invoice

DS = "http://www.w3.org/2000/09/xmldsig#"
NS = {
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "ds": DS,
}


@pytest.fixture(scope="module")
def key_and_cert():
    return make_test_certificate()


@pytest.fixture()
def signed(generate, invoice_dto, key_and_cert):
    key, cert = key_and_cert
    return XmlSigner(key, cert).sign(generate(invoice_dto).raw)


def test_signature_verifies_with_the_certificate(signed, key_and_cert):
    verify_signature(signed, key_and_cert[1])


def test_signature_is_inside_extension_content_with_the_announced_id(signed):
    root = etree.fromstring(signed)
    sig = root.xpath("ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent/ds:Signature", namespaces=NS)
    assert len(sig) == 1
    assert len(root.xpath("//ds:Signature", namespaces=NS)) == 1
    assert sig[0].get("Id") == root.xpath("cac:Signature/cbc:ID/text()", namespaces=NS)[0] == "SIGN-ABC"
    assert sig[0].prefix == "ds"


def test_signature_algorithms_and_reference(signed):
    root = etree.fromstring(signed)
    get = lambda xp: root.xpath(xp, namespaces=NS)[0]  # noqa: E731
    assert get("//ds:SignatureMethod/@Algorithm") == "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
    assert get("//ds:DigestMethod/@Algorithm") == "http://www.w3.org/2001/04/xmlenc#sha256"
    assert get("//ds:CanonicalizationMethod/@Algorithm") == "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
    assert get("//ds:Reference/@URI") == ""
    assert "http://www.w3.org/2000/09/xmldsig#enveloped-signature" in root.xpath(
        "//ds:Transform/@Algorithm", namespaces=NS
    )
    assert root.xpath("//ds:KeyInfo/ds:X509Data/ds:X509Certificate", namespaces=NS)


def test_signed_xml_still_complies_with_the_xsd(signed):
    validate_invoice(signed)


def test_signed_xml_is_iso_8859_1(signed):
    assert signed.startswith(b'<?xml version="1.0" encoding="ISO-8859-1"?>')
    assert "Tingo María".encode("iso-8859-1") in signed


def test_altering_an_amount_breaks_the_signature(signed, key_and_cert):  # AC-2
    tampered = signed.replace(b">377.67</cbc:PayableAmount>", b">1.00</cbc:PayableAmount>")
    assert tampered != signed
    with pytest.raises((InvalidDigest, InvalidSignature)):
        verify_signature(tampered, key_and_cert[1])


def test_another_certificate_does_not_verify(signed):
    _, other = make_test_certificate()
    with pytest.raises((InvalidDigest, InvalidSignature)):
        verify_signature(signed, other)


def test_digest_value_is_the_document_hash(signed):  # R-07
    value = digest_value(signed)
    assert len(value) == 44 and value.endswith("=")  # SHA-256 in base64


def test_expired_certificate_is_rejected(generate, invoice_dto):  # AC-3
    key, cert = make_test_certificate(not_before=datetime.now(timezone.utc) - timedelta(days=400), days=365)
    with pytest.raises(SigningConfigurationError, match="expired"):
        XmlSigner(key, cert).sign(generate(invoice_dto).raw)


def test_already_signed_xml_is_not_signed_again(signed, key_and_cert):
    with pytest.raises(SigningConfigurationError):
        XmlSigner(*key_and_cert).sign(signed)


def test_loads_a_pfx_and_rejects_a_wrong_password(tmp_path, key_and_cert, generate, invoice_dto):
    pfx = tmp_path / "cert.pfx"
    pfx.write_bytes(to_pkcs12(*key_and_cert, password="secreto"))
    signed = XmlSigner.from_pkcs12(pfx, "secreto").sign(generate(invoice_dto).raw)
    verify_signature(signed, key_and_cert[1])
    with pytest.raises(SigningConfigurationError, match="password"):
        XmlSigner.from_pkcs12(pfx, "otra")
