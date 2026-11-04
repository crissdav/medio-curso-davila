from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from lxml import etree

from abc_invoicing.adapters.ubl.invoice_generator import UblInvoiceGenerator
from abc_invoicing.application.invoice_mapper import CompanyProfile, invoice_from_dto

ROOT = Path(__file__).resolve().parents[1]
NS = {
    "inv": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
}


class Xml:
    """Generated XML with short XPath helpers."""

    def __init__(self, raw: bytes) -> None:
        self.raw = raw
        self.root = etree.fromstring(raw)

    def all(self, xpath: str) -> list:
        return self.root.xpath(xpath, namespaces=NS)

    def text(self, xpath: str) -> str:
        found = self.all(xpath)
        assert len(found) == 1, f"{xpath}: expected 1 node, found {len(found)}"
        return found[0] if isinstance(found[0], str) else found[0].text

    def attr(self, xpath: str, name: str) -> str | None:
        found = self.all(xpath)
        assert len(found) == 1, f"{xpath}: expected 1 node, found {len(found)}"
        return found[0].get(name)


@pytest.fixture(scope="session")
def company() -> CompanyProfile:
    return CompanyProfile.from_dict(json.loads((ROOT / "tests" / "fixtures" / "company.json").read_text(encoding="utf-8")))


@pytest.fixture(scope="session")
def generator() -> UblInvoiceGenerator:
    return UblInvoiceGenerator()


@pytest.fixture()
def invoice_dto() -> dict:
    """Reference invoice F001-123: groceries with ISC (catalog 08) and ICBPER."""
    return json.loads((ROOT / "specs" / "schemas" / "examples" / "invoice-response.json").read_text(encoding="utf-8"))


@pytest.fixture()
def generate(generator, company):
    """Generates the XML of a DTO; generate() raises if it breaks the XSD."""

    def _generate(dto: dict) -> Xml:
        return Xml(generator.generate(invoice_from_dto(copy.deepcopy(dto), company)))

    return _generate


@pytest.fixture()
def reference_xml() -> etree._Element:
    parser = etree.XMLParser(remove_comments=True, remove_blank_text=True)
    return etree.parse(str(ROOT / "specs" / "ref" / "20123456786-01-F001-123.xml"), parser).getroot()
