"""Domain model of the invoice. Pure Python: no XML, no framework (ADR-002)."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal

INVOICE = "01"
SALES_RECEIPT = "03"
RUC_DOCUMENT = "6"
ANONYMOUS_DOCUMENT = "-"
RECEIPT_ID_THRESHOLD = Decimal("700")  # Current value of the S/ 700 parameter (SPEC-001 R-04).
RUC_WEIGHTS = (5, 4, 3, 2, 7, 6, 5, 4, 3, 2)
RUC_PREFIXES = ("10", "15", "16", "17", "20")
SERIES_PATTERN = re.compile(r"[FB][A-Z0-9]{3}")
MAX_SEQUENCE_NUMBER = 99_999_999
CURRENCIES = frozenset({"PEN", "USD", "EUR"})  # Catalog 02.
# Phase 1 scope (SPEC-011 R-03): domestic sales, without IVAP (17) or exports (40).
DOMESTIC_SALE = "0101"
ONEROUS_AFFECTATIONS = frozenset({"10", "20", "30"})
FREE_AFFECTATIONS = frozenset({"11", "12", "13", "14", "15", "16", "21", "31", "32", "33", "34", "35", "36", "37"})
TOTALS_TOLERANCE = Decimal("1.00")  # INV-04.


class DomainError(ValueError):
    """A domain invariant was broken."""


def is_valid_ruc(ruc: str) -> bool:
    """Format and modulus 11 check digit (SPEC-004 R-01)."""
    if len(ruc) != 11 or not ruc.isdigit() or not ruc.startswith(RUC_PREFIXES):
        return False
    remainder = sum(weight * int(digit) for weight, digit in zip(RUC_WEIGHTS, ruc)) % 11
    return (11 - remainder) % 10 == int(ruc[10])


@dataclass(frozen=True)
class Issuer:
    ruc: str
    legal_name: str
    ubigeo: str
    address: str
    trade_name: str | None = None
    establishment: str = "0000"

    def __post_init__(self) -> None:
        if not is_valid_ruc(self.ruc):
            raise DomainError(f"Invalid issuer RUC: {self.ruc}")


# Catalog 06: format of the customer document number, with the message shown when it does not match.
IDENTITY_DOCUMENT_RULES = {
    "6": (re.compile(r"(10|15|16|17|20)[0-9]{9}"), "RUC: 11 digits starting with 10, 15, 16, 17 or 20"),
    "1": (re.compile(r"[0-9]{8}"), "DNI: 8 digits"),
    "4": (re.compile(r"[A-Za-z0-9]{1,12}"), "Foreigner ID card: up to 12 letters or digits"),
    "7": (re.compile(r"[A-Za-z0-9]{1,12}"), "Passport: up to 12 letters or digits"),
    "A": (re.compile(r"[A-Za-z0-9]{1,15}"), "Diplomatic ID card: up to 15 letters or digits"),
    "0": (re.compile(r".{1,15}"), "Non-domiciled tax document: up to 15 characters"),
    "-": (re.compile(r"-?"), "Varios: no document number"),
}


@dataclass(frozen=True)
class Customer:
    document_type: str
    document_number: str
    legal_name: str
    address: str | None = None

    def __post_init__(self) -> None:
        rule = IDENTITY_DOCUMENT_RULES.get(self.document_type)
        if rule is None:
            raise DomainError(f"Identity document type not in catalog 06: {self.document_type}")
        pattern, description = rule
        if not pattern.fullmatch(self.document_number):
            raise DomainError(f"Invalid customer document number '{self.document_number}': {description}")
        if self.document_type == RUC_DOCUMENT and not is_valid_ruc(self.document_number):
            raise DomainError(f"Invalid customer RUC '{self.document_number}': the check digit does not match")
        if not self.legal_name.strip():
            raise DomainError("The customer name is required")


@dataclass(frozen=True)
class IscConfig:
    """ISC calculation system, catalog 08."""

    system: str
    rate: Decimal | None = None
    fixed_amount: Decimal | None = None
    unit_conversion_factor: Decimal = Decimal("1")
    retail_price: Decimal | None = None


@dataclass(frozen=True)
class DocumentLine:
    """Line with the amounts already calculated by the domain (SPEC-003)."""

    line_number: int
    description: str
    quantity: Decimal
    unit_of_measure: str
    unit_value: Decimal
    igv_affectation: str
    unit_price: Decimal
    sale_value: Decimal
    igv_base: Decimal
    igv_rate: Decimal
    igv: Decimal
    total_taxes: Decimal
    product_code: str | None = None
    sunat_product_code: str | None = None
    discount: Decimal | None = None
    isc: IscConfig | None = None
    isc_base: Decimal = Decimal("0.00")
    isc_amount: Decimal = Decimal("0.00")
    icbper_bag_count: int | None = None
    icbper_unit_amount: Decimal | None = None
    icbper: Decimal = Decimal("0.00")


@dataclass(frozen=True)
class Installment:
    amount: Decimal
    due_date: date


@dataclass(frozen=True)
class PaymentTerms:
    """Literal SUNAT values: Contado (cash) or Credito (credit)."""

    type: str = "Contado"
    pending_amount: Decimal | None = None
    installments: tuple[Installment, ...] = ()

    def __post_init__(self) -> None:
        if self.type == "Credito":
            if self.pending_amount is None or not self.installments:
                raise DomainError("Credit terms require a pending amount and installments")
            if sum(i.amount for i in self.installments) != self.pending_amount:
                raise DomainError("Installments must add up to the pending amount")


@dataclass(frozen=True)
class Totals:
    taxed_total: Decimal
    exempt_total: Decimal
    unaffected_total: Decimal
    free_total: Decimal
    isc_total: Decimal
    igv_total: Decimal
    icbper_total: Decimal
    tax_total: Decimal
    sale_value_total: Decimal
    sale_price_total: Decimal
    discount_total: Decimal
    payable_amount: Decimal
    amount_in_words: str
    rounding: Decimal | None = None


@dataclass(frozen=True)
class Invoice:
    """Invoice (01) or sales receipt (03)."""

    document_type: str
    series: str
    sequence_number: int
    operation_type: str
    issue_date: date
    currency: str
    issuer: Issuer
    customer: Customer
    lines: tuple[DocumentLine, ...]
    totals: Totals
    payment_terms: PaymentTerms = field(default_factory=PaymentTerms)
    issue_time: time | None = None

    def __post_init__(self) -> None:
        if not self.lines:
            raise DomainError("INV-01: a document needs at least one line")
        if not SERIES_PATTERN.fullmatch(self.series):
            raise DomainError(f"Invalid series: {self.series}")
        if not 1 <= self.sequence_number <= MAX_SEQUENCE_NUMBER:
            raise DomainError(f"Sequence number out of range: {self.sequence_number}")
        if self.currency not in CURRENCIES:
            raise DomainError(f"Currency not in catalog 02: {self.currency}")
        if self.operation_type != DOMESTIC_SALE:
            raise DomainError(f"Operation type not supported in phase 1: {self.operation_type}")
        for line in self.lines:
            if line.igv_affectation not in ONEROUS_AFFECTATIONS | FREE_AFFECTATIONS:
                raise DomainError(f"IGV affectation not supported in phase 1: {line.igv_affectation}")
            if line.icbper_bag_count and Decimal(line.icbper_bag_count) != line.quantity:
                # SUNAT error 3236: cbc:BaseUnitMeasure must equal cbc:InvoicedQuantity.
                raise DomainError(
                    f"Line {line.line_number}: ICBPER applies to plastic bags, so the bag count "
                    f"({line.icbper_bag_count}) must equal the quantity ({line.quantity}) (SUNAT 3236)"
                )
        self._check_totals()
        if self.document_type == INVOICE:
            if not self.series.startswith("F"):
                raise DomainError("INV-02: an invoice requires an F series")
            if self.customer.document_type != RUC_DOCUMENT or not is_valid_ruc(self.customer.document_number):
                raise DomainError("INV-02: an invoice requires a customer with a valid RUC")
        elif self.document_type == SALES_RECEIPT:
            if not self.series.startswith("B"):
                raise DomainError("INV-03: a sales receipt requires a B series")
            if self.customer.document_type == ANONYMOUS_DOCUMENT and self.totals.payable_amount > RECEIPT_ID_THRESHOLD:
                raise DomainError("INV-03: a sales receipt above the threshold must identify the customer")
        else:
            raise DomainError(f"Unsupported document type: {self.document_type}")

    def _check_totals(self) -> None:
        """INV-04: the amounts of the document must add up."""
        t = self.totals
        if t.isc_total + t.igv_total + t.icbper_total != t.tax_total:
            raise DomainError("INV-04: taxTotal differs from ISC + IGV + ICBPER")
        expected = t.sale_value_total + t.tax_total - t.discount_total + (t.rounding or Decimal("0"))
        if abs(expected - t.payable_amount) > TOTALS_TOLERANCE:
            raise DomainError(f"INV-04: payable amount {t.payable_amount} differs from {expected}")

    @property
    def number(self) -> str:
        """Series and number as they go in cbc:ID (T-05)."""
        return f"{self.series}-{self.sequence_number}"

    @property
    def file_name(self) -> str:
        """SPEC-006 R-08: {RUC}-{TYPE}-{SERIES}-{NUMBER}.xml, number padded to 8 digits.

        20123456786-01-F001-00000123.xml. The CDR returned by SUNAT/OSE uses the same name with "R-".
        """
        return f"{self.issuer.ruc}-{self.document_type}-{self.series}-{self.sequence_number:08d}.xml"
