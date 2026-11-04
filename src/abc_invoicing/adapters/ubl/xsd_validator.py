"""Validation against the official OASIS UBL 2.1 XSD (SPEC-006 R-04)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from lxml import etree

INVOICE_XSD = (
    Path(__file__).resolve().parents[4]
    / "specs"
    / "ubl"
    / "xsd"
    / "maindoc"
    / "UBL-Invoice-2.1.xsd"
)
EXT_NS = (
    "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
)


class XsdValidationError(ValueError):
    """The XML does not comply with the official XSD."""


@lru_cache(maxsize=1)
def _schema() -> etree.XMLSchema:
    return etree.XMLSchema(etree.parse(str(INVOICE_XSD)))


def validate_invoice(xml: bytes) -> None:
    """Raise XsdValidationError if the XML breaks the XSD.

    The XSD requires an element inside ext:ExtensionContent, which only exists after signing
    (SPEC-006 R-05). An empty one is filled with a placeholder here, only for this check.
    """
    tree = etree.fromstring(xml)
    for content in tree.iter(f"{{{EXT_NS}}}ExtensionContent"):
        if len(content) == 0:
            etree.SubElement(
                content, "{urn:abc:signature-pending}SignaturePending"
            )
    schema = _schema()
    if not schema.validate(tree):
        errors = "; ".join(
            f"line {e.line}: {e.message}" for e in schema.error_log
        )
        raise XsdValidationError(errors)
