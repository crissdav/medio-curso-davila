"""Maps the Invoice DTO (specs/schemas/invoice.schema.json) to the domain aggregate."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, time
from decimal import Decimal
from typing import Any

from ..domain.models import Customer, DocumentLine, Installment, Invoice, IscConfig, Issuer, PaymentTerms, Totals

ICBPER_PER_BAG = Decimal("0.50")  # Current value of the ICBPER parameter (SPEC-003).


@dataclass(frozen=True)
class CompanyProfile:
    """Company data that the DTO does not carry: fiscal address and product master."""

    ubigeo: str
    address: str
    sunat_product_codes: Mapping[str, str]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> CompanyProfile:
        return cls(data["ubigeo"], data["address"], data.get("sunatProductCodes", {}))


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _isc(data: Mapping[str, Any] | None) -> IscConfig | None:
    if data is None:
        return None
    return IscConfig(
        system=data["system"],
        rate=_decimal(data.get("rate")),
        fixed_amount=_decimal(data.get("fixedAmount")),
        unit_conversion_factor=Decimal(data.get("unitConversionFactor", "1")),
        retail_price=_decimal(data.get("retailPrice")),
    )


def _line(data: Mapping[str, Any], company: CompanyProfile) -> DocumentLine:
    bags = data.get("icbperBagCount")
    return DocumentLine(
        line_number=data["lineNumber"],
        description=data["description"],
        quantity=Decimal(data["quantity"]),
        unit_of_measure=data["unitOfMeasure"],
        unit_value=Decimal(data["unitValue"]),
        igv_affectation=data["igvAffectation"],
        unit_price=Decimal(data["unitPrice"]),
        sale_value=Decimal(data["saleValue"]),
        igv_base=Decimal(data["igvBase"]),
        igv_rate=Decimal(data.get("igvRate", "0")),
        igv=Decimal(data["igv"]),
        total_taxes=Decimal(data["totalTaxes"]),
        product_code=data.get("productCode"),
        sunat_product_code=company.sunat_product_codes.get(data.get("productCode")),
        discount=_decimal(data.get("discount")),
        isc=_isc(data.get("isc")),
        isc_base=Decimal(data.get("iscBase", "0.00")),
        isc_amount=Decimal(data.get("iscAmount", "0.00")),
        icbper_bag_count=bags,
        icbper_unit_amount=ICBPER_PER_BAG if bags else None,
        icbper=Decimal(data.get("icbper", "0.00")),
    )


def _payment_terms(data: Mapping[str, Any] | None) -> PaymentTerms:
    if data is None:
        return PaymentTerms()
    return PaymentTerms(
        type=data["type"],
        pending_amount=_decimal(data.get("pendingAmount")),
        installments=tuple(
            Installment(Decimal(i["amount"]), date.fromisoformat(i["dueDate"])) for i in data.get("installments", ())
        ),
    )


def _totals(data: Mapping[str, Any]) -> Totals:
    return Totals(
        taxed_total=Decimal(data["taxedTotal"]),
        exempt_total=Decimal(data["exemptTotal"]),
        unaffected_total=Decimal(data["unaffectedTotal"]),
        free_total=Decimal(data["freeTotal"]),
        isc_total=Decimal(data["iscTotal"]),
        igv_total=Decimal(data["igvTotal"]),
        icbper_total=Decimal(data["icbperTotal"]),
        tax_total=Decimal(data["taxTotal"]),
        sale_value_total=Decimal(data["saleValueTotal"]),
        sale_price_total=Decimal(data["salePriceTotal"]),
        discount_total=Decimal(data["discountTotal"]),
        payable_amount=Decimal(data["payableAmount"]),
        amount_in_words=data["amountInWords"],
        rounding=_decimal(data.get("rounding")),
    )


def invoice_from_dto(dto: Mapping[str, Any], company: CompanyProfile) -> Invoice:
    issuer, customer = dto["issuer"], dto["customer"]
    return Invoice(
        document_type=dto["documentType"],
        series=dto["series"],
        sequence_number=dto["sequenceNumber"],
        operation_type=dto["operationType"],
        issue_date=date.fromisoformat(dto["issueDate"]),
        issue_time=time.fromisoformat(dto["issueTime"]) if dto.get("issueTime") else None,
        currency=dto["currency"],
        issuer=Issuer(
            ruc=issuer["ruc"],
            legal_name=issuer["legalName"],
            trade_name=issuer.get("tradeName"),
            establishment=issuer.get("establishment", "0000"),
            ubigeo=company.ubigeo,
            address=company.address,
        ),
        customer=Customer(
            document_type=customer["documentType"],
            document_number=customer["documentNumber"],
            legal_name=customer["legalName"],
            address=customer.get("address"),
        ),
        lines=tuple(_line(line, company) for line in dto["items"]),
        totals=_totals(dto["totals"]),
        payment_terms=_payment_terms(dto.get("paymentTerms")),
    )
