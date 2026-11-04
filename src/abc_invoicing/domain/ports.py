"""Output ports required by the domain (ADR-002)."""
from __future__ import annotations

from typing import Protocol

from .models import Invoice


class UblGeneratorPort(Protocol):
    def generate(self, invoice: Invoice) -> bytes:
        """Translate the aggregate into UBL 2.1 XML according to the traceability matrix."""
        ...
