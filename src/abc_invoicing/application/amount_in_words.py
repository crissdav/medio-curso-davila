"""Amount in words for cbc:Note languageLocaleID="1000" (matrix T-08).

377.67 PEN → "TRESCIENTOS SETENTA Y SIETE CON 67/100 SOLES"
"""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

CURRENCY_NAMES = {"PEN": "SOLES", "USD": "DÓLARES AMERICANOS", "EUR": "EUROS"}

_UNITS = (
    "", "UNO", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE", "DIEZ",
    "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISÉIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE", "VEINTE",
    "VEINTIUNO", "VEINTIDÓS", "VEINTITRÉS", "VEINTICUATRO", "VEINTICINCO", "VEINTISÉIS", "VEINTISIETE",
    "VEINTIOCHO", "VEINTINUEVE",
)
_TENS = ("", "", "", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA")
_HUNDREDS = (
    "", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS",
    "OCHOCIENTOS", "NOVECIENTOS",
)


def _below_thousand(n: int, apocope: bool = False) -> str:
    """0–999. With apocope, a final UNO becomes UN before MIL / MILLONES (VEINTIÚN MIL)."""
    if n == 100:
        return "CIEN"
    hundreds, rest = divmod(n, 100)
    if rest < 30:
        tail = _UNITS[rest]
    else:
        tens, units = divmod(rest, 10)
        tail = _TENS[tens] + (f" Y {_UNITS[units]}" if units else "")
    if apocope:
        tail = "VEINTIÚN" if tail == "VEINTIUNO" else tail[:-1] if tail.endswith("UNO") else tail
    return " ".join(part for part in (_HUNDREDS[hundreds], tail) if part)


def integer_in_words(n: int) -> str:
    if not 0 <= n < 1_000_000_000:
        raise ValueError(f"Amount out of range: {n}")
    if n == 0:
        return "CERO"
    millions, rest = divmod(n, 1_000_000)
    thousands, units = divmod(rest, 1000)
    parts = []
    if millions:
        parts.append("UN MILLÓN" if millions == 1 else f"{_below_thousand(millions, apocope=True)} MILLONES")
    if thousands:
        parts.append("MIL" if thousands == 1 else f"{_below_thousand(thousands, apocope=True)} MIL")
    if units:
        parts.append(_below_thousand(units))
    return " ".join(parts)


def amount_in_words(amount: Decimal, currency: str = "PEN") -> str:
    """Integer part in words and cents as NN/100, followed by the currency name."""
    amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    integer = int(amount)
    cents = int((amount - integer) * 100)
    return f"{integer_in_words(integer)} CON {cents:02d}/100 {CURRENCY_NAMES[currency]}"
