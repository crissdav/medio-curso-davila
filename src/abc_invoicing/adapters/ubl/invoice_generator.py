"""Generates the UBL 2.1 Invoice XML with the SUNAT customization (SPEC-006).

The XML is built from classes generated from the official XSD (generated.py), never from text
templates. Each block cites its row of the traceability matrix (docs/05-traceability-matrix.md).
"""

from __future__ import annotations

from datetime import date, time
from decimal import Decimal

from xsdata.formats.dataclass.serializers import XmlSerializer
from xsdata.formats.dataclass.serializers.config import SerializerConfig
from xsdata.models.datatype import XmlDate, XmlTime

from ...domain.models import (
    FREE_AFFECTATIONS,
    Customer,
    DocumentLine,
    Invoice,
    Issuer,
    Totals,
)
from . import generated as ubl
from .xsd_validator import validate_invoice

SUNAT = "PE:SUNAT"
CATALOG_URI = "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo"
UN_ECE = "United Nations Economic Commission for Europe"
NAMESPACES = {
    None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
    "ds": "http://www.w3.org/2000/09/xmldsig#",
}

# Catalog 05: tax code → (name, international code).
ISC_TAX = "2000"
IGV_TAX = "1000"
EXEMPT_TAX = "9997"
UNAFFECTED_TAX = "9998"
FREE_TAX = "9996"
EXPORT_TAX = "9995"
IVAP_TAX = "1016"
ICBPER_TAX = "7152"
TAX_SCHEMES = {
    IGV_TAX: ("IGV", "VAT"),
    IVAP_TAX: ("IVAP", "VAT"),
    ISC_TAX: ("ISC", "EXC"),
    ICBPER_TAX: ("ICBPER", "OTH"),
    EXPORT_TAX: ("EXP", "FRE"),
    FREE_TAX: ("GRA", "FRE"),
    EXEMPT_TAX: ("EXO", "VAT"),
    UNAFFECTED_TAX: ("INA", "FRE"),
}
# Catalog 07: IGV affectation → tax of catalog 05.
AFFECTATION_TAX = {
    "10": IGV_TAX,
    "17": IVAP_TAX,
    "20": EXEMPT_TAX,
    "30": UNAFFECTED_TAX,
    "40": EXPORT_TAX,
    **{code: FREE_TAX for code in FREE_AFFECTATIONS},
}
ONEROUS_PRICE = "01"  # Catalog 16.
REFERENCE_VALUE = "02"  # Catalog 16.
LINE_DISCOUNT_REASON = "00"  # Catalog 53.


def _percent(rate: Decimal) -> Decimal:
    """0.18 → 18. Avoids exponents such as 2E+1 for round values."""
    value = rate * 100
    return (
        value.quantize(Decimal(1))
        if value == value.to_integral_value()
        else value.normalize()
    )


def _tax_scheme(tax: str) -> ubl.TaxScheme:
    name, international_code = TAX_SCHEMES[tax]
    return ubl.TaxScheme(
        id=ubl.Id(value=tax),
        name=ubl.Name(value=name),
        tax_type_code=ubl.TaxTypeCode(value=international_code),
    )


def _party_id(document_type: str, number: str) -> ubl.PartyIdentification:
    """T-12, T-16, T-17: identity document, catalog 06."""
    return ubl.PartyIdentification(
        id=ubl.Id(
            value=number,
            scheme_id=document_type,
            scheme_name="Documento de Identidad",
            scheme_agency_name=SUNAT,
            scheme_uri=f"{CATALOG_URI}06",
        )
    )


XML_ENCODING = "ISO-8859-1"


class UblInvoiceGenerator:
    """Implements UblGeneratorPort. The XML is checked against the XSD before it is returned."""

    def __init__(self, signature_id: str = "SIGN-ABC") -> None:
        self._signature_id = signature_id
        self._serializer = XmlSerializer(
            config=SerializerConfig(encoding=XML_ENCODING, indent="  ")
        )

    def generate(self, invoice: Invoice) -> bytes:
        # SPEC-006 R-09: ISO-8859-1. Characters outside Latin-1 become numeric references (&#8364;).
        xml = self._serializer.render(
            self.build(invoice), ns_map=NAMESPACES
        ).encode(XML_ENCODING, errors="xmlcharrefreplace")
        validate_invoice(xml)
        return xml

    def build(self, invoice: Invoice) -> ubl.Invoice:
        return ubl.Invoice(
            # T-03: the signature is inserted here when signing (SPEC-006 R-05).
            ublextensions=ubl.Ublextensions(
                ublextension=[
                    ubl.Ublextension(extension_content=ubl.ExtensionContent())
                ]
            ),
            ublversion_id=ubl.UblversionId(value="2.1"),  # T-01
            customization_id=ubl.CustomizationId(
                value="2.0", scheme_agency_name=SUNAT
            ),  # T-02
            id=ubl.Id(value=invoice.number),  # T-05
            issue_date=ubl.IssueDate(
                value=_xml_date(invoice.issue_date)
            ),  # T-06
            issue_time=ubl.IssueTime(value=_xml_time(invoice.issue_time))
            if invoice.issue_time
            else None,  # T-07
            invoice_type_code=ubl.InvoiceTypeCode(  # T-08, T-09
                value=invoice.document_type,
                list_id=invoice.operation_type,
                list_agency_name=SUNAT,
                list_name="Tipo de Documento",
                list_uri=f"{CATALOG_URI}01",
            ),
            note=[
                ubl.Note(
                    value=invoice.totals.amount_in_words,
                    language_locale_id="1000",
                )
            ],  # T-10
            document_currency_code=ubl.DocumentCurrencyCode(  # T-11
                value=invoice.currency,
                list_id="ISO 4217 Alpha",
                list_agency_name=UN_ECE,
            ),
            signature=[self._signature(invoice.issuer)],  # T-04
            accounting_supplier_party=ubl.AccountingSupplierParty(
                party=_issuer_party(invoice.issuer)
            ),
            accounting_customer_party=ubl.AccountingCustomerParty(
                party=_customer_party(invoice.customer)
            ),
            payment_terms=_payment_terms(invoice),
            tax_total=[_header_tax_total(invoice)],
            legal_monetary_total=_monetary_total(
                invoice.totals, invoice.currency
            ),
            invoice_line=[
                _line(line, invoice.currency) for line in invoice.lines
            ],
        )

    def _signature(self, issuer: Issuer) -> ubl.Signature1:
        return ubl.Signature1(
            id=ubl.Id(value=self._signature_id),
            signatory_party=ubl.SignatoryParty(
                party_identification=[
                    ubl.PartyIdentification(id=ubl.Id(value=issuer.ruc))
                ],
                party_name=[
                    ubl.PartyName(name=ubl.Name(value=issuer.legal_name))
                ],
            ),
            digital_signature_attachment=ubl.DigitalSignatureAttachment(
                external_reference=ubl.ExternalReference(
                    uri=ubl.Uri(value=f"#{self._signature_id}")
                )
            ),
        )


def _xml_date(value: date) -> XmlDate:
    return XmlDate(
        value.year, value.month, value.day
    )  # No time zone: 2026-10-22, not 2026-10-22Z.


def _xml_time(value: time) -> XmlTime:
    return XmlTime(value.hour, value.minute, value.second)


def _issuer_party(issuer: Issuer) -> ubl.Party:
    return ubl.Party(
        party_identification=[_party_id("6", issuer.ruc)],  # T-12
        party_name=[ubl.PartyName(name=ubl.Name(value=issuer.trade_name))]
        if issuer.trade_name
        else [],  # T-14
        party_legal_entity=[
            ubl.PartyLegalEntity(
                registration_name=ubl.RegistrationName(
                    value=issuer.legal_name
                ),  # T-13
                registration_address=ubl.RegistrationAddress(
                    id=ubl.Id(
                        value=issuer.ubigeo,
                        scheme_name="Ubigeos",
                        scheme_agency_name="PE:INEI",
                    ),
                    address_type_code=ubl.AddressTypeCode(
                        value=issuer.establishment
                    ),  # T-15
                    address_line=[
                        ubl.AddressLine(line=ubl.Line(value=issuer.address))
                    ],
                    country=ubl.Country(
                        identification_code=ubl.IdentificationCode(value="PE")
                    ),
                ),
            )
        ],
    )


def _customer_party(customer: Customer) -> ubl.Party:
    address = None
    if customer.address:
        address = ubl.RegistrationAddress(
            address_line=[
                ubl.AddressLine(line=ubl.Line(value=customer.address))
            ],  # T-19
            country=ubl.Country(
                identification_code=ubl.IdentificationCode(value="PE")
            ),
        )
    return ubl.Party(
        party_identification=[
            _party_id(customer.document_type, customer.document_number)
        ],  # T-16, T-17
        party_legal_entity=[
            ubl.PartyLegalEntity(
                registration_name=ubl.RegistrationName(
                    value=customer.legal_name
                ),  # T-18
                registration_address=address,
            )
        ],
    )


def _payment_terms(invoice: Invoice) -> list[ubl.PaymentTerms]:
    """T-20 … T-22 (RS 000193-2020/SUNAT, Annex IV)."""
    terms = invoice.payment_terms
    means = ubl.PaymentMeansId(value=terms.type)
    if terms.type != "Credito":
        return [
            ubl.PaymentTerms(
                id=ubl.Id(value="FormaPago"), payment_means_id=[means]
            )
        ]
    result = [
        ubl.PaymentTerms(
            id=ubl.Id(value="FormaPago"),
            payment_means_id=[means],
            amount=ubl.Amount(
                value=terms.pending_amount, currency_id=invoice.currency
            ),
        )
    ]
    for number, installment in enumerate(terms.installments, start=1):
        result.append(
            ubl.PaymentTerms(
                id=ubl.Id(value="FormaPago"),
                payment_means_id=[
                    ubl.PaymentMeansId(value=f"Cuota{number:03d}")
                ],
                amount=ubl.Amount(
                    value=installment.amount, currency_id=invoice.currency
                ),
                payment_due_date=ubl.PaymentDueDate(
                    value=_xml_date(installment.due_date)
                ),
            )
        )
    return result


def _subtotal(
    tax: str,
    tax_amount: Decimal,
    currency: str,
    taxable: Decimal | None = None,
) -> ubl.TaxSubtotal:
    return ubl.TaxSubtotal(
        taxable_amount=ubl.TaxableAmount(value=taxable, currency_id=currency)
        if taxable is not None
        else None,
        tax_amount=ubl.TaxAmount(value=tax_amount, currency_id=currency),
        tax_category=ubl.TaxCategory(tax_scheme=_tax_scheme(tax)),
    )


def _header_tax_total(invoice: Invoice) -> ubl.TaxTotal:
    """T-23 … T-29: only taxes present in the document are reported."""
    totals, currency = invoice.totals, invoice.currency
    subtotals = []
    if totals.isc_total:
        isc_base = sum(
            (line.isc_base for line in invoice.lines if line.isc),
            Decimal("0.00"),
        )
        subtotals.append(
            _subtotal(ISC_TAX, totals.isc_total, currency, isc_base)
        )  # T-28
    if totals.taxed_total:
        subtotals.append(
            _subtotal(IGV_TAX, totals.igv_total, currency, totals.taxed_total)
        )  # T-24
    if totals.exempt_total:
        subtotals.append(
            _subtotal(
                EXEMPT_TAX, Decimal("0.00"), currency, totals.exempt_total
            )
        )  # T-25
    if totals.unaffected_total:
        subtotals.append(
            _subtotal(
                UNAFFECTED_TAX,
                Decimal("0.00"),
                currency,
                totals.unaffected_total,
            )
        )  # T-26
    if totals.free_total:
        free_tax = sum(
            (
                line.igv
                for line in invoice.lines
                if line.igv_affectation in FREE_AFFECTATIONS
            ),
            Decimal("0.00"),
        )
        subtotals.append(
            _subtotal(FREE_TAX, free_tax, currency, totals.free_total)
        )  # T-27
    if totals.icbper_total:
        subtotals.append(
            _subtotal(ICBPER_TAX, totals.icbper_total, currency)
        )  # T-29
    return ubl.TaxTotal(
        tax_amount=ubl.TaxAmount(value=totals.tax_total, currency_id=currency),
        tax_subtotal=subtotals,
    )


def _monetary_total(totals: Totals, currency: str) -> ubl.LegalMonetaryTotal:
    """T-30 … T-34."""
    return ubl.LegalMonetaryTotal(
        line_extension_amount=ubl.LineExtensionAmount(
            value=totals.sale_value_total, currency_id=currency
        ),
        tax_inclusive_amount=ubl.TaxInclusiveAmount(
            value=totals.sale_price_total, currency_id=currency
        ),
        allowance_total_amount=ubl.AllowanceTotalAmount(
            value=totals.discount_total, currency_id=currency
        )
        if totals.discount_total
        else None,
        payable_rounding_amount=ubl.PayableRoundingAmount(
            value=totals.rounding, currency_id=currency
        )
        if totals.rounding
        else None,
        payable_amount=ubl.PayableAmount(
            value=totals.payable_amount, currency_id=currency
        ),
    )


def _line(line: DocumentLine, currency: str) -> ubl.InvoiceLine:
    """T-40 … T-55."""
    free = line.igv_affectation in FREE_AFFECTATIONS
    return ubl.InvoiceLine(
        id=ubl.Id(value=str(line.line_number)),
        invoiced_quantity=ubl.InvoicedQuantity(
            value=line.quantity,
            unit_code=line.unit_of_measure,
            unit_code_list_id="UN/ECE rec 20",
        ),
        line_extension_amount=ubl.LineExtensionAmount(
            value=line.sale_value, currency_id=currency
        ),
        pricing_reference=ubl.PricingReference(  # T-43, T-44
            alternative_condition_price=[
                ubl.AlternativeConditionPrice(
                    price_amount=ubl.PriceAmount(
                        value=line.unit_price, currency_id=currency
                    ),
                    price_type_code=ubl.PriceTypeCode(
                        value=REFERENCE_VALUE if free else ONEROUS_PRICE,
                        list_name="Tipo de Precio",
                        list_agency_name=SUNAT,
                        list_uri=f"{CATALOG_URI}16",
                    ),
                )
            ]
        ),
        allowance_charge=_line_discount(line, currency),
        tax_total=[_line_tax_total(line, currency)],
        item=_item(line),
        price=ubl.Price(
            price_amount=ubl.PriceAmount(
                value=line.unit_value, currency_id=currency
            )
        ),  # T-45
    )


def _line_discount(
    line: DocumentLine, currency: str
) -> list[ubl.AllowanceCharge]:
    """T-54: catalog 53 code 00."""
    if not line.discount:
        return []
    return [
        ubl.AllowanceCharge(
            charge_indicator=ubl.ChargeIndicator(value=False),
            allowance_charge_reason_code=ubl.AllowanceChargeReasonCode(
                value=LINE_DISCOUNT_REASON
            ),
            amount=ubl.Amount(value=line.discount, currency_id=currency),
        )
    ]


def _isc_percent(line: DocumentLine) -> Decimal:
    """T-52: SUNAT requires cbc:Percent on every line tax except ICBPER (error 2992).

    Systems 01 and 03 have a rate. System 02 (fixed amount) has none, so the effective rate
    iscAmount / iscBase is reported: 14.88 / 48.00 → 31.
    """
    if line.isc.rate is not None:
        return _percent(line.isc.rate)
    if not line.isc_base:
        return Decimal(0)
    return _percent((line.isc_amount / line.isc_base).quantize(Decimal("0.0000001")))


def _line_tax_total(line: DocumentLine, currency: str) -> ubl.TaxTotal:
    subtotals = []
    if (
        line.isc
    ):  # T-51, T-52: ISC comes first because it is part of the IGV base.
        subtotals.append(
            ubl.TaxSubtotal(
                taxable_amount=ubl.TaxableAmount(
                    value=line.isc_base, currency_id=currency
                ),
                tax_amount=ubl.TaxAmount(
                    value=line.isc_amount, currency_id=currency
                ),
                tax_category=ubl.TaxCategory(
                    percent=ubl.Percent(value=_isc_percent(line)),
                    tier_range=ubl.TierRange(value=line.isc.system),
                    tax_scheme=_tax_scheme(ISC_TAX),
                ),
            )
        )
    subtotals.append(  # T-49, T-50
        ubl.TaxSubtotal(
            taxable_amount=ubl.TaxableAmount(
                value=line.igv_base, currency_id=currency
            ),
            tax_amount=ubl.TaxAmount(value=line.igv, currency_id=currency),
            tax_category=ubl.TaxCategory(
                percent=ubl.Percent(value=_percent(line.igv_rate)),
                tax_exemption_reason_code=ubl.TaxExemptionReasonCode(
                    value=line.igv_affectation,
                    list_agency_name=SUNAT,
                    list_name="Afectacion del IGV",
                    list_uri=f"{CATALOG_URI}07",
                ),
                tax_scheme=_tax_scheme(AFFECTATION_TAX[line.igv_affectation]),
            ),
        )
    )
    if line.icbper_bag_count:  # T-53
        subtotals.append(
            ubl.TaxSubtotal(
                tax_amount=ubl.TaxAmount(
                    value=line.icbper, currency_id=currency
                ),
                base_unit_measure=ubl.BaseUnitMeasure(
                    value=Decimal(line.icbper_bag_count), unit_code="NIU"
                ),
                tax_category=ubl.TaxCategory(
                    per_unit_amount=ubl.PerUnitAmount(
                        value=line.icbper_unit_amount, currency_id=currency
                    ),
                    tax_scheme=_tax_scheme(ICBPER_TAX),
                ),
            )
        )
    return ubl.TaxTotal(
        tax_amount=ubl.TaxAmount(value=line.total_taxes, currency_id=currency),
        tax_subtotal=subtotals,
    )  # T-55


def _item(line: DocumentLine) -> ubl.Item:
    return ubl.Item(
        description=[ubl.Description(value=line.description)],  # T-46
        sellers_item_identification=(  # T-47
            ubl.SellersItemIdentification(id=ubl.Id(value=line.product_code))
            if line.product_code
            else None
        ),
        commodity_classification=(  # T-48
            [
                ubl.CommodityClassification(
                    item_classification_code=ubl.ItemClassificationCode(
                        value=line.sunat_product_code,
                        list_id="UNSPSC",
                        list_agency_name="GS1 US",
                        list_name="Item Classification",
                    )
                )
            ]
            if line.sunat_product_code
            else []
        ),
    )
