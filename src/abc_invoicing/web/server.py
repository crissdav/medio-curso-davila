"""Small local web app: a form that generates the signed XML (python -m abc_invoicing.web).

Routes:
  GET  /               the form (static/index.html)
  GET  /api/defaults   issuer data, catalogs and whether a certificate is available
  POST /api/preview    form → calculated lines and totals (SPEC-003), without generating
  POST /api/generate   form → signed XML in ISO-8859-1, named {RUC}-{TYPE}-{SERIES}-{NUMBER}.xml

It only listens on 127.0.0.1: the signing key must not be reachable from the network (ADR-003).
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..adapters.signature.xml_signer import SigningConfigurationError, XmlSigner, digest_value
from ..adapters.ubl.invoice_generator import UblInvoiceGenerator
from ..adapters.ubl.xsd_validator import XsdValidationError
from ..application.invoice_mapper import CompanyProfile, invoice_from_dto
from ..application.tax_calculator import FormError, build_invoice_dto
from ..domain.models import DomainError

STATIC = Path(__file__).resolve().parent / "static"
REPO = Path(__file__).resolve().parents[3]
CATALOGS = REPO / "specs" / "catalogs"


# Catalog 06 for the form: the rule of each type is shown in the list and enforced while typing.
# The domain checks the same formats (IDENTITY_DOCUMENT_RULES), so these are only a guide.
IDENTITY_DOCUMENTS = [
    {"code": "6", "name": "RUC", "rule": "11 dígitos", "maxLength": 11, "minLength": 11, "numeric": True,
     "hint": "11 dígitos, empieza con 10, 15, 16, 17 o 20 y con dígito verificador válido. Obligatorio en facturas."},
    {"code": "1", "name": "DNI", "rule": "8 dígitos", "maxLength": 8, "minLength": 8, "numeric": True,
     "hint": "8 dígitos."},
    {"code": "4", "name": "Carnet de extranjería", "rule": "hasta 12 caracteres", "maxLength": 12, "minLength": 1,
     "numeric": False, "hint": "Hasta 12 letras o números, sin espacios ni guiones."},
    {"code": "7", "name": "Pasaporte", "rule": "hasta 12 caracteres", "maxLength": 12, "minLength": 1,
     "numeric": False, "hint": "Hasta 12 letras o números, sin espacios ni guiones."},
    {"code": "-", "name": "Varios", "rule": "sin documento", "maxLength": 0, "minLength": 0, "numeric": False,
     "hint": "Sin documento: solo en boletas de hasta S/ 700."},
]


@dataclass
class AppConfig:
    issuer: dict[str, str]
    company: dict[str, Any]
    signer: XmlSigner | None
    signer_note: str


def _catalog(name: str) -> list[dict[str, str]]:
    data = json.loads((CATALOGS / name).read_text(encoding="utf-8"))
    return [{"code": c["code"], "name": c["officialName"]} for c in data["codes"]]


def generate(form: dict[str, Any], config: AppConfig, sign: bool = True) -> dict[str, Any]:
    dto = build_invoice_dto(form)
    issuer = form.get("issuer") or {}
    company = CompanyProfile.from_dict(
        {
            "ubigeo": str(issuer.get("ubigeo") or config.company["ubigeo"]).strip(),
            "address": str(issuer.get("address") or config.company["address"]).strip(),
            "sunatProductCodes": config.company.get("sunatProductCodes", {}),
        }
    )
    invoice = invoice_from_dto(dto, company)
    xml = UblInvoiceGenerator().generate(invoice)  # Validated against the XSD (SPEC-006 R-04).
    signed = bool(sign and config.signer)
    if signed:
        xml = config.signer.sign(xml)
    return {
        "fileName": invoice.file_name,
        "signed": signed,
        "digestValue": digest_value(xml) if signed else None,
        "xmlBase64": base64.b64encode(xml).decode("ascii"),
        "dto": dto,
    }


def make_handler(config: AppConfig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        server_version = "abc-invoicing"

        def log_message(self, fmt: str, *args: Any) -> None:  # Quieter console: one line per API call.
            if self.path.startswith("/api/"):
                super().log_message(fmt, *args)

        def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: HTTPStatus, data: Any) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self) -> None:  # noqa: N802
            if self.path in ("/", "/index.html"):
                self._send(HTTPStatus.OK, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/defaults":
                self._json(
                    HTTPStatus.OK,
                    {
                        "issuer": config.issuer | {"address": config.company["address"], "ubigeo": config.company["ubigeo"]},
                        "units": _catalog("cat-03-unit-of-measure.json"),
                        "identityDocuments": IDENTITY_DOCUMENTS,
                        "affectations": [
                            {"code": "10", "name": "Gravado"},
                            {"code": "20", "name": "Exonerado"},
                            {"code": "30", "name": "Inafecto"},
                        ],  # Catalog 07, short names for the form.
                        "canSign": config.signer is not None,
                        "signerNote": config.signer_note,
                    },
                )
            else:
                self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

        def do_POST(self) -> None:  # noqa: N802
            try:
                length = int(self.headers.get("Content-Length", 0))
                form = json.loads(self.rfile.read(length) or b"{}")
            except (ValueError, json.JSONDecodeError):
                self._json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
                return
            try:
                if self.path == "/api/preview":
                    dto = build_invoice_dto(form)
                    self._json(HTTPStatus.OK, {"items": dto["items"], "totals": dto["totals"], "paymentTerms": dto["paymentTerms"]})
                elif self.path == "/api/generate":
                    self._json(HTTPStatus.OK, generate(form, config, sign=bool(form.get("sign", True))))
                else:
                    self._json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            except (FormError, DomainError, SigningConfigurationError, XsdValidationError) as exc:
                self._json(HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(exc), "type": type(exc).__name__})

    return Handler


def load_config(company_path: Path, cert: Path | None, password: str | None, create_test_cert: bool) -> AppConfig:
    company = json.loads(company_path.read_text(encoding="utf-8"))
    issuer = {
        "ruc": company.get("ruc", "20123456786"),
        "legalName": company.get("legalName", "ABC SOFTWARE CORP S.A.C."),
        "tradeName": company.get("tradeName", "ABC ABARROTES"),
    }
    signer, note = None, "No certificate: the XML is generated unsigned."
    if cert:
        if not cert.exists() and create_test_cert:
            from ..adapters.signature.test_certificate import make_test_certificate, to_pkcs12

            key, certificate = make_test_certificate(issuer["ruc"], issuer["legalName"])
            cert.write_bytes(to_pkcs12(key, certificate, password))
            print(f"Created the test certificate {cert.name} (no legal value).")
        if cert.exists():
            signer = XmlSigner.from_pkcs12(cert, password)
            note = f"Signed with {cert.name}."
    return AppConfig(issuer, company, signer, note)


def serve(config: AppConfig, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), make_handler(config))


def default_password() -> str:
    return os.environ.get("ABC_CERT_PASSWORD", "123456")
