"""Builds the invoice DTO from form data, calculating every amount (SPEC-003).

The form only carries what a person types: customer, products, quantities and unit values without IGV.
This module applies the SPEC-003 rules to obtain the line amounts and the totals that the generator
expects (specs/schemas/examples/invoice-response.json).

Scope of the form: IGV affectations 10 (taxed), 20 (exempt) and 30 (unaffected), ICBPER, cash or credit.
ISC, discounts and free-of-charge lines are still available through the JSON input of the CLI.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any

from .amount_in_words import amount_in_words
from .invoice_mapper import ICBPER_PER_BAG

IGV_RATE = Decimal("0.18")
TAXED, EXEMPT, UNAFFECTED = "10", "20", "30"
FORM_AFFECTATIONS = (TAXED, EXEMPT, UNAFFECTED)
CENT = Decimal("0.01")
UNIT_PRECISION = Decimal("0.0000000001")  # R-10: up to 10 decimals for unit values.
DOMESTIC_SALE = "0101"


class FormError(ValueError):
    """The form data is incomplete or invalid."""


def _round2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _text(value: Decimal, min_decimals: int = 2) -> str:
    """Plain decimal text without exponents: at least min_decimals, no trailing zeros beyond them."""
    integer, _, decimals = format(value.normalize(), "f").partition(".")
    decimals = decimals.ljust(min_decimals, "0")
    return f"{integer}.{decimals}" if decimals else integer


def _amount(value: Decimal) -> str:
    return format(_round2(value), "f")


def _decimal(value: Any, field: str, positive: bool = True) -> Decimal:
    try:
        number = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise FormError(f"{field}: '{value}' is not a number") from None
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise FormError(f"{field} must be greater than zero" if positive else f"{field} cannot be negative")
    return number


def calculate_line(number: int, item: Mapping[str, Any]) -> dict[str, Any]:
    description = str(item.get("description", "")).strip()
    if not description:
        raise FormError(f"Line {number}: the description is required")
    affectation = str(item.get("igvAffectation", TAXED))
    if affectation not in FORM_AFFECTATIONS:
        raise FormError(f"Line {number}: IGV affectation {affectation} is not supported by the form")
    quantity = _decimal(item.get("quantity"), f"Line {number}: quantity")
    unit_value = _decimal(item.get("unitValue"), f"Line {number}: unit value")
    # R-06: ICBPER is charged per plastic bag, so on a bag line the bag count is the quantity (SUNAT 3236).
    if str(item.get("icbper", "")).lower() in ("true", "1", "on"):
        if quantity != quantity.to_integral_value():
            raise FormError(f"Line {number}: plastic bags are counted in whole units")
        bags = int(quantity)
    else:
        bags = int(_decimal(item.get("icbperBagCount") or 0, f"Line {number}: bags", positive=False))
    if bags and bags != quantity:
        raise FormError(f"Line {number}: the bag count ({bags}) must equal the quantity ({_text(quantity, 0)}) (SUNAT 3236)")

    sale_value = _round2(quantity * unit_value)  # R-01
    rate = IGV_RATE if affectation == TAXED else Decimal(0)
    igv = _round2(sale_value * rate)  # R-03, R-04: without ISC, the IGV base is the sale value.
    icbper = _round2(bags * ICBPER_PER_BAG)  # R-06: not part of the IGV base.
    unit_price = ((sale_value + igv) / quantity).quantize(UNIT_PRECISION, rounding=ROUND_HALF_UP)  # R-08

    line = {
        "lineNumber": number,
        "description": description,
        "quantity": _text(quantity, 0),
        "unitOfMeasure": str(item.get("unitOfMeasure") or "NIU"),
        "unitValue": _text(unit_value),
        "igvAffectation": affectation,
        "unitPrice": _text(unit_price),
        "saleValue": _amount(sale_value),
        "iscBase": "0.00",
        "iscAmount": "0.00",
        "igvBase": _amount(sale_value),
        "igvRate": _text(rate) if rate else "0",
        "igv": _amount(igv),
        "icbper": _amount(icbper),
        "totalTaxes": _amount(igv + icbper),
    }
    if code := str(item.get("productCode") or "").strip():
        line["productCode"] = code
    if bags:
        line["icbperBagCount"] = bags
    return line


def calculate_totals(lines: list[dict[str, Any]], currency: str) -> dict[str, str]:
    def total(affectation: str) -> Decimal:
        return sum((Decimal(l["saleValue"]) for l in lines if l["igvAffectation"] == affectation), Decimal(0))

    taxed, exempt, unaffected = total(TAXED), total(EXEMPT), total(UNAFFECTED)
    igv = _round2(taxed * IGV_RATE)  # R-09: on the taxed total, within ±1.00 of the line sum.
    icbper = sum((Decimal(l["icbper"]) for l in lines), Decimal(0))
    sale_value = taxed + exempt + unaffected
    tax = igv + icbper
    payable = sale_value + tax
    return {
        "taxedTotal": _amount(taxed),
        "exemptTotal": _amount(exempt),
        "unaffectedTotal": _amount(unaffected),
        "freeTotal": "0.00",
        "iscTotal": "0.00",
        "igvTotal": _amount(igv),
        "icbperTotal": _amount(icbper),
        "taxTotal": _amount(tax),
        "saleValueTotal": _amount(sale_value),
        "salePriceTotal": _amount(payable),
        "discountTotal": "0.00",
        "payableAmount": _amount(payable),
        "amountInWords": amount_in_words(payable, currency),
    }


def _payment_terms(data: Mapping[str, Any] | None, payable: Decimal, issue_date: date) -> dict[str, Any]:
    if not data or data.get("type", "Contado") == "Contado":
        return {"type": "Contado"}
    rows = list(data.get("installments") or [{}])
    given = [str(r.get("amount") or "").strip() for r in rows]
    if all(given):
        amounts = [_decimal(a, f"Installment {i}: amount") for i, a in enumerate(given, 1)]
    elif not any(given):  # Split the total into equal installments; the last one absorbs the cents.
        share = _round2(payable / len(rows))
        amounts = [share] * (len(rows) - 1) + [payable - share * (len(rows) - 1)]
    else:
        raise FormError("Fill in every installment amount, or leave them all empty to split the total equally")
    installments = []
    for i, (row, amount) in enumerate(zip(rows, amounts), 1):
        due = row.get("dueDate") or (issue_date + timedelta(days=30 * i)).isoformat()
        try:
            due_date = date.fromisoformat(due)
        except ValueError:
            raise FormError(f"Installment {i}: '{due}' is not a date") from None
        if due_date <= issue_date:
            raise FormError(f"Installment {i}: the due date must be after the issue date")
        installments.append({"amount": _amount(amount), "dueDate": due})
    return {"type": "Credito", "pendingAmount": _amount(payable), "installments": installments}


def build_invoice_dto(form: Mapping[str, Any]) -> dict[str, Any]:
    """Form data → invoice DTO with every amount calculated."""
    items = [i for i in form.get("items", []) if any(str(v).strip() for v in i.values())]
    if not items:
        raise FormError("Add at least one product")
    currency = form.get("currency", "PEN")
    lines = [calculate_line(n, item) for n, item in enumerate(items, 1)]
    totals = calculate_totals(lines, currency)
    try:
        sequence = int(form.get("sequenceNumber"))
        issue_date = date.fromisoformat(form.get("issueDate") or date.today().isoformat())
    except (TypeError, ValueError):
        raise FormError("Check the number and the issue date of the document") from None
    series = str(form.get("series", "")).strip().upper()
    customer = {k: str(v).strip() for k, v in (form.get("customer") or {}).items() if v not in (None, "")}
    customer.setdefault("documentType", "-")
    customer.setdefault("documentNumber", "")  # Empty values reach the domain, which explains what is missing.
    customer.setdefault("legalName", "")
    if customer["documentType"] == "-":
        customer.update(documentNumber="-", legalName=customer.get("legalName") or "VARIOS")
    issuer = form.get("issuer") or {}
    return {
        "documentType": form.get("documentType", "01"),
        "series": series,
        "sequenceNumber": sequence,
        "number": f"{series}-{sequence:08d}",
        "operationType": DOMESTIC_SALE,
        "issueDate": issue_date.isoformat(),
        "issueTime": form.get("issueTime") or None,
        "currency": currency,
        "issuer": {
            "ruc": str(issuer.get("ruc", "")).strip(),
            "legalName": str(issuer.get("legalName", "")).strip(),
            "tradeName": str(issuer.get("tradeName", "")).strip() or None,
            "establishment": "0000",
        },
        "customer": customer,
        "items": lines,
        "paymentTerms": _payment_terms(form.get("paymentTerms"), Decimal(totals["payableAmount"]), issue_date),
        "totals": totals,
    }
