"""Unit tests of the UBL 2.1 invoice generation (SPEC-006). T-nn = row of the traceability matrix."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from lxml import etree

from abc_invoicing.adapters.ubl.invoice_generator import (
    AFFECTATION_TAX,
    FREE_AFFECTATIONS,
    TAX_SCHEMES,
    UblInvoiceGenerator,
)
from abc_invoicing.adapters.ubl.xsd_validator import XsdValidationError, validate_invoice
from abc_invoicing.application.invoice_mapper import invoice_from_dto
from abc_invoicing.domain.models import DomainError, is_valid_ruc

ROOT = Path(__file__).resolve().parents[1]
FIRST_LINE = "//cac:InvoiceLine[cbc:ID='1']"
BEER_LINE = "//cac:InvoiceLine[cbc:ID='2']"
SOFT_DRINK_LINE = "//cac:InvoiceLine[cbc:ID='3']"
BAG_LINE = "//cac:InvoiceLine[cbc:ID='4']"


def tax_subtotal(prefix: str, tax: str) -> str:
    return f"{prefix}/cac:TaxTotal/cac:TaxSubtotal[cac:TaxCategory/cac:TaxScheme/cbc:ID='{tax}']"


def differences(actual, expected, path="") -> list[str]:
    """Structural comparison: names, attributes, text and order, ignoring indentation."""
    here = f"{path}/{etree.QName(expected).localname}"
    found = []
    if actual.tag != expected.tag:
        return [f"{here}: element {actual.tag}"]
    if dict(actual.attrib) != dict(expected.attrib):
        found.append(f"{here}: attributes {dict(actual.attrib)} != {dict(expected.attrib)}")
    if (actual.text or "").strip() != (expected.text or "").strip():
        found.append(f"{here}: text {actual.text!r} != {expected.text!r}")
    if len(actual) != len(expected):
        found.append(f"{here}: {len(actual)} children != {len(expected)}")
    for a, e in zip(actual, expected):
        found.extend(differences(a, e, here))
    return found


# ---------- Whole document ----------

def test_generated_xml_equals_the_reference_invoice(generate, invoice_dto, reference_xml):
    xml = generate(invoice_dto)
    assert differences(xml.root, reference_xml) == []


def test_generated_xml_complies_with_the_official_xsd(generate, invoice_dto):
    validate_invoice(generate(invoice_dto).raw)


def test_is_iso_8859_1_with_xml_declaration_and_named_prefixes(generate, invoice_dto):
    raw = generate(invoice_dto).raw
    assert raw.startswith(b'<?xml version="1.0" encoding="ISO-8859-1"?>')
    assert b"<cbc:ID>" in raw and b"<cac:Signature>" in raw and b"ns0:" not in raw
    assert "Tingo María".encode("iso-8859-1") in raw
    assert "Tingo María".encode("utf-8") not in raw


def test_characters_outside_latin1_become_numeric_references(generate, invoice_dto):
    invoice_dto["customer"]["legalName"] = "CAFÉ € “ÑANDÚ”"
    xml = generate(invoice_dto)
    assert b"CAF\xc9 &#8364; &#8220;\xd1AND\xda&#8221;" in xml.raw
    assert "CAFÉ € “ÑANDÚ”" in etree.tostring(xml.root, encoding="unicode")


def test_xsd_rejects_a_broken_document(generate, invoice_dto):
    root = generate(invoice_dto).root
    root.remove(root.find("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID"))
    root.insert(len(root), etree.Element("{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}ID"))
    with pytest.raises(XsdValidationError):
        validate_invoice(etree.tostring(root))


def test_generator_never_returns_xml_that_breaks_the_xsd(company, invoice_dto):
    class BrokenGenerator(UblInvoiceGenerator):  # SPEC-006 R-04: validated before signing.
        def build(self, invoice):
            document = super().build(invoice)
            document.id = None  # cbc:ID is mandatory in UBL-Invoice-2.1.xsd.
            return document

    with pytest.raises(XsdValidationError):
        BrokenGenerator().generate(invoice_from_dto(invoice_dto, company))


def test_generation_is_deterministic(generate, invoice_dto):
    assert generate(invoice_dto).raw == generate(invoice_dto).raw


# ---------- Header ----------

def test_ubl_version_and_sunat_customization(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.text("/inv:Invoice/cbc:UBLVersionID") == "2.1"  # T-01
    assert xml.text("/inv:Invoice/cbc:CustomizationID") == "2.0"  # T-02
    assert xml.attr("/inv:Invoice/cbc:CustomizationID", "schemeAgencyName") == "PE:SUNAT"


def test_signature_slot_is_ready_for_signing(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert len(xml.all("//ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent")) == 1  # T-03
    assert xml.text("//cac:Signature/cac:SignatoryParty/cac:PartyIdentification/cbc:ID") == "20123456786"  # T-04


def test_series_and_number_without_leading_zeros(generate, invoice_dto):
    assert generate(invoice_dto).text("/inv:Invoice/cbc:ID") == "F001-123"  # T-05


def test_dates_have_no_time_zone(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.text("/inv:Invoice/cbc:IssueDate") == "2026-10-22"  # T-06
    assert xml.text("/inv:Invoice/cbc:IssueTime") == "10:15:00"  # T-07


def test_document_and_operation_type(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.text("/inv:Invoice/cbc:InvoiceTypeCode") == "01"  # T-08
    assert xml.attr("/inv:Invoice/cbc:InvoiceTypeCode", "listID") == "0101"  # T-09
    assert xml.attr("/inv:Invoice/cbc:InvoiceTypeCode", "listAgencyName") == "PE:SUNAT"


def test_amount_in_words_legend(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.text("/inv:Invoice/cbc:Note[@languageLocaleID='1000']") == invoice_dto["totals"]["amountInWords"]  # T-10


# ---------- Parties ----------

def test_issuer_identified_with_ruc(generate, invoice_dto):
    xml = generate(invoice_dto)
    party = "//cac:AccountingSupplierParty/cac:Party"
    assert xml.text(f"{party}/cac:PartyIdentification/cbc:ID") == "20123456786"  # T-12
    assert xml.attr(f"{party}/cac:PartyIdentification/cbc:ID", "schemeID") == "6"
    assert xml.text(f"{party}/cac:PartyName/cbc:Name") == "ABC ABARROTES"  # T-14
    assert xml.text(f"{party}/cac:PartyLegalEntity/cbc:RegistrationName") == "ABC SOFTWARE CORP S.A.C."  # T-13
    assert xml.text(f"{party}/cac:PartyLegalEntity/cac:RegistrationAddress/cbc:AddressTypeCode") == "0000"  # T-15


def test_customer_identified_according_to_catalog_06(generate, invoice_dto):
    xml = generate(invoice_dto)
    party = "//cac:AccountingCustomerParty/cac:Party"
    assert xml.attr(f"{party}/cac:PartyIdentification/cbc:ID", "schemeID") == "6"  # T-16
    assert xml.text(f"{party}/cac:PartyIdentification/cbc:ID") == "20601234565"  # T-17
    assert xml.text(f"{party}/cac:PartyLegalEntity/cbc:RegistrationName") == "BODEGA LA ESQUINA S.A.C."  # T-18
    assert xml.text(f"{party}/cac:PartyLegalEntity/cac:RegistrationAddress/cac:AddressLine/cbc:Line") == "Av. Raymondi 123, Tingo María"  # T-19


def test_special_characters_are_escaped(generate, invoice_dto):
    invoice_dto["customer"]["legalName"] = "PEÑA & HIJOS <S.A.C.>"
    xml = generate(invoice_dto)
    assert b"PE\xd1A &amp; HIJOS &lt;S.A.C.&gt;" in xml.raw
    assert xml.text("//cac:AccountingCustomerParty//cbc:RegistrationName") == "PEÑA & HIJOS <S.A.C.>"


# ---------- Payment terms ----------

def test_cash_payment_terms(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.text("//cac:PaymentTerms[cbc:ID='FormaPago']/cbc:PaymentMeansID") == "Contado"  # T-20
    assert xml.all("//cac:PaymentTerms/cbc:Amount") == []


def test_credit_payment_terms_with_installments(generate, invoice_dto):
    invoice_dto["paymentTerms"] = {
        "type": "Credito",
        "pendingAmount": "377.67",
        "installments": [
            {"amount": "200.00", "dueDate": "2026-11-22"},
            {"amount": "177.67", "dueDate": "2026-12-22"},
        ],
    }
    xml = generate(invoice_dto)
    assert xml.all("//cac:PaymentTerms/cbc:PaymentMeansID/text()") == ["Credito", "Cuota001", "Cuota002"]  # T-20, T-22
    assert xml.text("//cac:PaymentTerms[cbc:PaymentMeansID='Credito']/cbc:Amount") == "377.67"  # T-21
    assert xml.text("//cac:PaymentTerms[cbc:PaymentMeansID='Cuota002']/cbc:Amount") == "177.67"
    assert xml.text("//cac:PaymentTerms[cbc:PaymentMeansID='Cuota002']/cbc:PaymentDueDate") == "2026-12-22"


def test_credit_installments_must_add_up(company, invoice_dto):
    invoice_dto["paymentTerms"] = {"type": "Credito", "pendingAmount": "377.67", "installments": [{"amount": "1.00", "dueDate": "2026-11-22"}]}
    with pytest.raises(DomainError):
        invoice_from_dto(invoice_dto, company)


# ---------- Totals ----------

def test_header_taxes_and_totals(generate, invoice_dto):
    xml = generate(invoice_dto)
    head = "/inv:Invoice"
    assert xml.text(f"{head}/cac:TaxTotal/cbc:TaxAmount") == "81.50"  # T-23
    assert xml.text(tax_subtotal(head, "1000") + "/cbc:TaxableAmount") == "296.17"  # T-24
    assert xml.text(tax_subtotal(head, "1000") + "/cbc:TaxAmount") == "57.46"
    assert xml.text(tax_subtotal(head, "2000") + "/cbc:TaxableAmount") == "96.00"  # T-28
    assert xml.text(tax_subtotal(head, "2000") + "/cbc:TaxAmount") == "23.04"
    assert xml.text(tax_subtotal(head, "7152") + "/cbc:TaxAmount") == "1.00"  # T-29
    assert xml.text("//cac:LegalMonetaryTotal/cbc:LineExtensionAmount") == "296.17"  # T-30
    assert xml.text("//cac:LegalMonetaryTotal/cbc:TaxInclusiveAmount") == "377.67"  # T-31
    assert xml.text("//cac:LegalMonetaryTotal/cbc:PayableAmount") == "377.67"  # T-34


def test_only_present_taxes_are_reported(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.all("/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID/text()") == ["2000", "1000", "7152"]
    assert xml.all("//cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount") == []


def test_every_amount_carries_the_document_currency(generate, invoice_dto):
    invoice_dto["currency"] = "USD"
    xml = generate(invoice_dto)
    assert xml.text("/inv:Invoice/cbc:DocumentCurrencyCode") == "USD"  # T-11
    assert set(xml.all("//@currencyID")) == {"USD"}


# ---------- Lines ----------

def test_taxed_line(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.text(f"{FIRST_LINE}/cbc:InvoicedQuantity") == "10"  # T-41
    assert xml.attr(f"{FIRST_LINE}/cbc:InvoicedQuantity", "unitCode") == "NIU"
    assert xml.attr(f"{FIRST_LINE}/cbc:InvoicedQuantity", "unitCodeListID") == "UN/ECE rec 20"
    assert xml.text(f"{FIRST_LINE}/cbc:LineExtensionAmount") == "200.00"  # T-42
    assert xml.text(f"{FIRST_LINE}/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceAmount") == "23.60"  # T-43
    assert xml.text(f"{FIRST_LINE}/cac:PricingReference/cac:AlternativeConditionPrice/cbc:PriceTypeCode") == "01"
    assert xml.text(f"{FIRST_LINE}/cac:Price/cbc:PriceAmount") == "20.00"  # T-45
    assert xml.text(f"{FIRST_LINE}/cac:Item/cbc:Description") == "Arroz extra bolsa 5 kg"  # T-46
    assert xml.text(f"{FIRST_LINE}/cac:Item/cac:SellersItemIdentification/cbc:ID") == "ARR-5KG"  # T-47
    assert xml.text(f"{FIRST_LINE}/cac:Item/cac:CommodityClassification/cbc:ItemClassificationCode") == "50221101"  # T-48
    igv = tax_subtotal(FIRST_LINE, "1000")
    assert xml.text(f"{igv}/cac:TaxCategory/cbc:TaxExemptionReasonCode") == "10"  # T-49
    assert xml.text(f"{igv}/cac:TaxCategory/cbc:Percent") == "18"  # T-50
    assert xml.text(f"{FIRST_LINE}/cac:TaxTotal/cbc:TaxAmount") == "36.00"  # T-55


def test_isc_fixed_amount_system(generate, invoice_dto):
    xml = generate(invoice_dto)
    isc = tax_subtotal(BEER_LINE, "2000")
    assert xml.text(f"{isc}/cac:TaxCategory/cbc:TierRange") == "02"  # T-51, catalog 08
    assert xml.text(f"{isc}/cbc:TaxAmount") == "14.88"  # T-52: 12 × 0.62 L × S/ 2.00
    # SUNAT error 2992: the rate is mandatory; system 02 reports the effective rate 14.88 / 48.00.
    assert xml.text(f"{isc}/cac:TaxCategory/cbc:Percent") == "31"
    assert xml.text(tax_subtotal(BEER_LINE, "1000") + "/cbc:TaxableAmount") == "62.88"  # ISC is part of the IGV base.


def test_isc_ad_valorem_system(generate, invoice_dto):
    xml = generate(invoice_dto)
    isc = tax_subtotal(SOFT_DRINK_LINE, "2000")
    assert xml.text(f"{isc}/cac:TaxCategory/cbc:TierRange") == "01"  # T-51
    assert xml.text(f"{isc}/cac:TaxCategory/cbc:Percent") == "17"  # T-52


def test_isc_precedes_igv_in_the_line(generate, invoice_dto):
    xml = generate(invoice_dto)
    assert xml.all(f"{BEER_LINE}/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID/text()") == ["2000", "1000"]


def test_icbper_line(generate, invoice_dto):
    xml = generate(invoice_dto)
    icbper = tax_subtotal(BAG_LINE, "7152")
    assert xml.text(f"{icbper}/cbc:BaseUnitMeasure") == "2"  # T-53
    assert xml.attr(f"{icbper}/cbc:BaseUnitMeasure", "unitCode") == "NIU"
    assert xml.text(f"{icbper}/cac:TaxCategory/cbc:PerUnitAmount") == "0.50"
    assert xml.text(f"{icbper}/cbc:TaxAmount") == "1.00"
    assert xml.all(f"{FIRST_LINE}//cac:TaxScheme[cbc:ID='7152']") == []


def test_line_discount(generate, invoice_dto):
    invoice_dto["items"][0]["discount"] = "5.00"
    xml = generate(invoice_dto)
    charge = f"{FIRST_LINE}/cac:AllowanceCharge"
    assert xml.text(f"{charge}/cbc:ChargeIndicator") == "false"  # T-54
    assert xml.text(f"{charge}/cbc:AllowanceChargeReasonCode") == "00"
    assert xml.text(f"{charge}/cbc:Amount") == "5.00"


def test_global_discount_and_rounding_totals(generate, invoice_dto):
    invoice_dto["totals"].update(discountTotal="5.00", rounding="0.03", payableAmount="372.70")
    xml = generate(invoice_dto)
    assert xml.text("//cac:LegalMonetaryTotal/cbc:AllowanceTotalAmount") == "5.00"  # T-32
    assert xml.text("//cac:LegalMonetaryTotal/cbc:PayableRoundingAmount") == "0.03"  # T-33


# ---------- Other operations ----------

def _single_line(dto: dict, **line) -> dict:
    base = dto["items"][0] | {"iscBase": "0.00", "iscAmount": "0.00", "icbper": "0.00"}
    dto["items"] = [base | line]
    return dto


@pytest.mark.parametrize(
    ("affectation", "tax", "name", "international", "total"),
    [("20", "9997", "EXO", "VAT", "exemptTotal"), ("30", "9998", "INA", "FRE", "unaffectedTotal")],
)
def test_exempt_and_unaffected_lines(generate, invoice_dto, affectation, tax, name, international, total):
    dto = _single_line(invoice_dto, igvAffectation=affectation, igv="0.00", igvRate="0", totalTaxes="0.00", unitPrice="20.00", igvBase="200.00")
    dto["totals"].update(taxedTotal="0.00", igvTotal="0.00", iscTotal="0.00", icbperTotal="0.00", taxTotal="0.00", salePriceTotal="200.00", saleValueTotal="200.00", payableAmount="200.00")
    dto["totals"][total] = "200.00"
    xml = generate(dto)
    line = tax_subtotal(FIRST_LINE, tax)  # T-25, T-26
    assert xml.text(f"{line}/cac:TaxCategory/cbc:TaxExemptionReasonCode") == affectation
    assert xml.text(f"{line}/cac:TaxCategory/cbc:Percent") == "0"
    assert xml.text(f"{line}/cac:TaxCategory/cac:TaxScheme/cbc:Name") == name
    assert xml.text(f"{line}/cac:TaxCategory/cac:TaxScheme/cbc:TaxTypeCode") == international
    assert xml.text(tax_subtotal("/inv:Invoice", tax) + "/cbc:TaxableAmount") == "200.00"
    assert xml.all("/inv:Invoice/cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cac:TaxScheme/cbc:ID/text()") == [tax]


def test_free_of_charge_line_uses_the_reference_value(generate, invoice_dto):
    dto = _single_line(invoice_dto, igvAffectation="21", unitValue="0", unitPrice="20.00", saleValue="200.00", igvBase="200.00", igv="0.00", igvRate="0", totalTaxes="0.00")
    dto["totals"].update(taxedTotal="0.00", freeTotal="200.00", igvTotal="0.00", iscTotal="0.00", icbperTotal="0.00", taxTotal="0.00", saleValueTotal="0.00", salePriceTotal="0.00", payableAmount="0.00")
    xml = generate(dto)
    price = f"{FIRST_LINE}/cac:PricingReference/cac:AlternativeConditionPrice"
    assert xml.text(f"{price}/cbc:PriceTypeCode") == "02"  # T-44, catalog 16
    assert xml.text(f"{price}/cbc:PriceAmount") == "20.00"
    assert xml.text(f"{FIRST_LINE}/cac:Price/cbc:PriceAmount") == "0"  # T-45
    assert xml.text(tax_subtotal("/inv:Invoice", "9996") + "/cbc:TaxableAmount") == "200.00"  # T-27
    assert xml.text(tax_subtotal(FIRST_LINE, "9996") + "/cac:TaxCategory/cac:TaxScheme/cbc:Name") == "GRA"


def _sales_receipt(dto: dict, customer: dict, total: str = "377.67") -> dict:
    dto.update(documentType="03", series="B001", customer=customer)
    dto["totals"]["payableAmount"] = total
    return dto


def test_sales_receipt_with_dni(generate, invoice_dto):
    xml = generate(_sales_receipt(invoice_dto, {"documentType": "1", "documentNumber": "12345678", "legalName": "ANA TORRES"}))
    assert xml.text("/inv:Invoice/cbc:ID") == "B001-123"
    assert xml.text("/inv:Invoice/cbc:InvoiceTypeCode") == "03"
    assert xml.attr("//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID", "schemeID") == "1"
    assert xml.all("//cac:AccountingCustomerParty//cac:RegistrationAddress") == []


def test_anonymous_sales_receipt_below_the_threshold(generate, invoice_dto):
    xml = generate(_sales_receipt(invoice_dto, {"documentType": "-", "documentNumber": "-", "legalName": "VARIOS"}))
    assert xml.attr("//cac:AccountingCustomerParty//cac:PartyIdentification/cbc:ID", "schemeID") == "-"


# ---------- Domain invariants ----------

@pytest.mark.parametrize(
    "change",
    [
        {"series": "B001"},  # INV-02
        {"customer": {"documentType": "1", "documentNumber": "12345678", "legalName": "X"}},  # INV-02
        {"customer": {"documentType": "6", "documentNumber": "20601234566", "legalName": "X"}},  # Wrong check digit.
        {"documentType": "03"},  # INV-03: F series on a sales receipt.
        {"items": []},  # INV-01
        {"documentType": "07"},  # Notes use their own UBL root.
        {"series": "F00a"},  # SPEC-005 R-01
        {"series": "F0001"},  # SPEC-005 R-01
        {"sequenceNumber": 0},  # SPEC-005 R-03
        {"sequenceNumber": 100000000},  # SPEC-005 R-03
        {"currency": "XXX"},  # Catalog 02
        {"operationType": "0200"},  # SPEC-011 R-03: phase 2.
    ],
)
def test_invalid_documents_never_reach_the_generator(company, invoice_dto, change):
    with pytest.raises(DomainError):
        invoice_from_dto(invoice_dto | change, company)


@pytest.mark.parametrize("affectation", ["17", "40", "99"])
def test_unsupported_igv_affectations_are_rejected(company, invoice_dto, affectation):
    invoice_dto["items"][0]["igvAffectation"] = affectation  # 17 and 40 are phase 2; 99 does not exist.
    with pytest.raises(DomainError):
        invoice_from_dto(invoice_dto, company)


@pytest.mark.parametrize(
    "change",
    [{"payableAmount": "1.00"}, {"taxTotal": "80.00"}, {"igvTotal": "50.00"}],
)
def test_totals_that_do_not_add_up_are_rejected(company, invoice_dto, change):
    invoice_dto["totals"].update(change)  # INV-04
    with pytest.raises(DomainError):
        invoice_from_dto(invoice_dto, company)


def test_rounding_tolerance_is_accepted(generate, invoice_dto):
    invoice_dto["totals"]["payableAmount"] = "378.00"  # INV-04: within ±1.00.
    assert generate(invoice_dto).text("//cac:LegalMonetaryTotal/cbc:PayableAmount") == "378.00"


def test_anonymous_sales_receipt_above_the_threshold_is_rejected(company, invoice_dto):
    dto = _sales_receipt(invoice_dto, {"documentType": "-", "documentNumber": "-", "legalName": "VARIOS"}, total="750.00")
    with pytest.raises(DomainError):
        invoice_from_dto(dto, company)


@pytest.mark.parametrize(("ruc", "valid"), [("20123456786", True), ("20123456787", False), ("30123456786", False), ("2012345678", False)])
def test_ruc_validation(ruc, valid):
    assert is_valid_ruc(ruc) is valid  # SPEC-004 AC-1, AC-2


# ---------- The code stays aligned with the specification ----------

def _catalog(name: str) -> dict:
    return json.loads((ROOT / "specs" / "catalogs" / name).read_text(encoding="utf-8"))


def test_tax_schemes_match_catalog_05():
    codes = {c["code"]: (c["name"], c["internationalCode"]) for c in _catalog("cat-05-taxes.json")["codes"]}
    for tax, scheme in TAX_SCHEMES.items():
        assert codes[tax] == scheme


def test_affectations_match_catalog_07():
    codes = _catalog("cat-07-igv-affectation.json")["codes"]
    assert {c["code"]: c["tax"] for c in codes} == AFFECTATION_TAX
    assert {c["code"] for c in codes if not c["onerous"]} == FREE_AFFECTATIONS


def test_generator_uses_classes_generated_from_the_xsd(company, invoice_dto):
    from abc_invoicing.adapters.ubl import generated

    built = UblInvoiceGenerator().build(invoice_from_dto(invoice_dto, company))
    assert isinstance(built, generated.Invoice)
    assert built.Meta.namespace == "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"


# ---------- File name (SPEC-006 R-08) ----------

@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({}, "20123456786-01-F001-00000123.xml"),
        ({"documentType": "03", "series": "B001", "sequenceNumber": 1,
          "customer": {"documentType": "1", "documentNumber": "45781236", "legalName": "ANA TORRES"}},
         "20123456786-03-B001-00000001.xml"),
        ({"sequenceNumber": 99_999_999}, "20123456786-01-F001-99999999.xml"),
    ],
)
def test_sunat_file_name(company, invoice_dto, changes, expected):
    invoice = invoice_from_dto(invoice_dto | changes, company)
    assert invoice.file_name == expected  # {RUC}-{TYPE}-{SERIES}-{NUMBER}.xml
