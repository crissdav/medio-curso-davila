"""Web form: amount in words, tax calculation (SPEC-003) and the local server (form → signed XML)."""
from __future__ import annotations

import base64
import json
import threading
import urllib.error
import urllib.request
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from abc_invoicing.adapters.signature.test_certificate import make_test_certificate, to_pkcs12
from abc_invoicing.adapters.signature.xml_signer import verify_signature
from abc_invoicing.adapters.ubl.xsd_validator import validate_invoice
from abc_invoicing.application.amount_in_words import amount_in_words
from abc_invoicing.application.tax_calculator import FormError, build_invoice_dto
from abc_invoicing.web.server import load_config, serve

ROOT = Path(__file__).resolve().parents[1]
CBC = "{urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2}"


# ---------- Amount in words (T-08) ----------

@pytest.mark.parametrize(
    ("amount", "currency", "expected"),
    [
        ("377.67", "PEN", "TRESCIENTOS SETENTA Y SIETE CON 67/100 SOLES"),
        ("51.75", "PEN", "CINCUENTA Y UNO CON 75/100 SOLES"),
        ("971.14", "PEN", "NOVECIENTOS SETENTA Y UNO CON 14/100 SOLES"),
        ("1", "PEN", "UNO CON 00/100 SOLES"),
        ("100", "PEN", "CIEN CON 00/100 SOLES"),
        ("0.50", "PEN", "CERO CON 50/100 SOLES"),
        ("1001", "PEN", "MIL UNO CON 00/100 SOLES"),
        ("21000", "PEN", "VEINTIÚN MIL CON 00/100 SOLES"),
        ("1250000.10", "USD", "UN MILLÓN DOSCIENTOS CINCUENTA MIL CON 10/100 DÓLARES AMERICANOS"),
    ],
)
def test_amount_in_words(amount, currency, expected):
    assert amount_in_words(Decimal(amount), currency) == expected


# ---------- Tax calculation (SPEC-003) ----------

def _form(**changes) -> dict:
    form = {
        "documentType": "01", "series": "F001", "sequenceNumber": 125, "issueDate": "2026-11-12", "issueTime": "12:00",
        "currency": "PEN",
        "issuer": {"ruc": "20123456786", "legalName": "ABC SOFTWARE CORP S.A.C.", "tradeName": "ABC ABARROTES"},
        "customer": {"documentType": "6", "documentNumber": "20609876540", "legalName": "DISTRIBUIDORA EL ÑANDÚ S.A.C."},
        "items": [
            {"description": "Azúcar rubia saco 50 kg", "quantity": "4", "unitValue": "120.00", "igvAffectation": "10"},
            {"description": "Plátano de seda", "unitOfMeasure": "KGM", "quantity": "3", "unitValue": "2.50", "igvAffectation": "20"},
            {"description": "Bolsa plástica", "quantity": "2", "unitValue": "0.0847", "igvAffectation": "10", "icbperBagCount": "2"},
        ],
        "paymentTerms": {"type": "Contado"},
    }
    form.update(changes)
    return form


def test_calculates_lines_and_totals():
    dto = build_invoice_dto(_form())
    sugar, plantain, bag = dto["items"]
    assert (sugar["saleValue"], sugar["igv"], sugar["unitPrice"]) == ("480.00", "86.40", "141.60")  # R-01, R-04, R-08
    assert (plantain["igv"], plantain["igvRate"], plantain["quantity"]) == ("0.00", "0", "3")  # Exempt.
    assert (bag["saleValue"], bag["igv"], bag["icbper"], bag["unitPrice"]) == ("0.17", "0.03", "1.00", "0.10")  # R-06
    t = dto["totals"]
    assert (t["taxedTotal"], t["exemptTotal"], t["igvTotal"], t["icbperTotal"]) == ("480.17", "7.50", "86.43", "1.00")
    assert t["payableAmount"] == "575.10"  # 480.17 + 7.50 + 86.43 + 1.00
    assert t["amountInWords"] == "QUINIENTOS SETENTA Y CINCO CON 10/100 SOLES"


def test_reproduces_the_hand_made_test_03():
    ref = json.loads((ROOT / "test_xml" / "03-F001-124" / "input.json").read_text(encoding="utf-8"))
    form = _form(customer=ref["customer"], sequenceNumber=124, items=[
        {k: i[k] for k in ("description", "quantity", "unitValue", "igvAffectation")} for i in ref["items"]
    ], paymentTerms={"type": "Credito", "installments": [{"dueDate": "2026-12-12"}, {"dueDate": "2027-01-11"}]})
    dto = build_invoice_dto(form)
    assert dto["totals"] == ref["totals"]
    assert dto["paymentTerms"] == ref["paymentTerms"]


def test_credit_split_absorbs_the_cents_in_the_last_installment():
    dto = build_invoice_dto(_form(paymentTerms={"type": "Credito", "installments": [{}, {}, {}]}))
    amounts = [Decimal(i["amount"]) for i in dto["paymentTerms"]["installments"]]
    assert sum(amounts) == Decimal(dto["totals"]["payableAmount"])
    assert [i["dueDate"] for i in dto["paymentTerms"]["installments"]] == ["2026-12-12", "2027-01-11", "2027-02-10"]


@pytest.mark.parametrize(
    "changes",
    [
        {"items": []},
        {"items": [{"description": "", "quantity": "1", "unitValue": "5"}]},
        {"items": [{"description": "X", "quantity": "0", "unitValue": "5"}]},
        {"items": [{"description": "X", "quantity": "abc", "unitValue": "5"}]},
        {"items": [{"description": "X", "quantity": "1", "unitValue": "5", "igvAffectation": "40"}]},
        {"paymentTerms": {"type": "Credito", "installments": [{"amount": "1.00"}, {}]}},
        {"paymentTerms": {"type": "Credito", "installments": [{"dueDate": "2026-11-01"}]}},
    ],
)
def test_rejects_invalid_form_data(changes):
    with pytest.raises(FormError):
        build_invoice_dto(_form(**changes))


# ---------- Local server ----------

@pytest.fixture(scope="module")
def server(tmp_path_factory):
    folder = tmp_path_factory.mktemp("web")
    key, cert = make_test_certificate()
    pfx = folder / "cert.pfx"
    pfx.write_bytes(to_pkcs12(key, cert, "clave"))
    config = load_config(ROOT / "tests" / "fixtures" / "company.json", pfx, "clave", create_test_cert=False)
    httpd = serve(config, port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}", cert
    httpd.shutdown()
    httpd.server_close()


def _post(url: str, body: dict) -> tuple[int, dict]:
    request = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def test_serves_the_form_and_the_defaults(server):
    url, _ = server
    with urllib.request.urlopen(url) as response:
        assert "Generar XML" in response.read().decode("utf-8")
    with urllib.request.urlopen(url + "/api/defaults") as response:
        defaults = json.loads(response.read())
    assert defaults["issuer"]["ruc"] == "20123456786"
    assert defaults["canSign"] is True
    assert {"10", "20", "30"} == {a["code"] for a in defaults["affectations"]}


def test_generate_returns_a_signed_iso_8859_1_xml_with_the_sunat_name(server):
    url, cert = server
    status, data = _post(url + "/api/generate", _form())
    assert status == 200
    assert data["fileName"] == "20123456786-01-F001-00000125.xml"  # SPEC-006 R-08
    xml = base64.b64decode(data["xmlBase64"])
    assert xml.startswith(b'<?xml version="1.0" encoding="ISO-8859-1"?>')
    assert "ÑANDÚ".encode("iso-8859-1") in xml
    validate_invoice(xml)
    verify_signature(xml, cert)
    assert etree.fromstring(xml).findtext(f".//{CBC}PayableAmount") == "575.10"


def test_generate_without_signature(server):
    url, _ = server
    status, data = _post(url + "/api/generate", _form(sign=False))
    assert status == 200 and data["signed"] is False
    assert b"<ext:ExtensionContent/>" in base64.b64decode(data["xmlBase64"])


@pytest.mark.parametrize(
    "changes",
    [
        {"customer": {"documentType": "1", "documentNumber": "45781236", "legalName": "ANA"}},  # Invoice needs a RUC.
        {"documentType": "03"},  # F series on a sales receipt.
        {"items": [{"description": "", "quantity": "1", "unitValue": "5"}]},
    ],
)
def test_invalid_documents_return_422_with_the_reason(server, changes):
    url, _ = server
    status, data = _post(url + "/api/generate", _form(**changes))
    assert status == 422 and data["error"]


def test_preview_calculates_without_generating(server):
    url, _ = server
    status, data = _post(url + "/api/preview", _form())
    assert status == 200
    assert data["totals"]["payableAmount"] == "575.10" and "xmlBase64" not in data


# ---------- ICBPER bags (SUNAT 3236) ----------

def test_icbper_checkbox_uses_the_quantity_as_bag_count():
    form = _form(items=[{"description": "Bolsa plástica", "quantity": "4", "unitValue": "0.0847", "icbper": True}])
    line = build_invoice_dto(form)["items"][0]
    assert (line["icbperBagCount"], line["icbper"]) == (4, "2.00")


@pytest.mark.parametrize(
    "item",
    [
        {"description": "Gaseosa", "quantity": "1", "unitValue": "1", "icbperBagCount": "4"},  # The case SUNAT rejected.
        {"description": "Bolsa", "quantity": "1.5", "unitValue": "0.10", "icbper": True},  # Bags are whole units.
    ],
)
def test_bag_count_different_from_the_quantity_is_rejected(item):
    with pytest.raises(FormError, match="3236|whole"):
        build_invoice_dto(_form(items=[item]))


# ---------- Customer document number (catalog 06) ----------

@pytest.mark.parametrize(
    ("document_type", "number", "message"),
    [
        ("1", "4578123", "DNI: 8 digits"),  # 7 digits.
        ("1", "457812361", "DNI: 8 digits"),  # 9 digits.
        ("1", "4578123A", "DNI: 8 digits"),
        ("6", "2060987654", "RUC: 11 digits"),  # 10 digits.
        ("6", "30609876540", "RUC: 11 digits"),  # Wrong prefix.
        ("6", "20609876541", "check digit"),
        ("7", "AB-123", "Passport"),
        ("4", "1234567890123", "Foreigner ID"),  # 13 characters.
        ("1", "", "DNI: 8 digits"),
    ],
)
def test_customer_document_number_follows_catalog_06(document_type, number, message):
    form = _form(documentType="03", series="B001",
                 customer={"documentType": document_type, "documentNumber": number, "legalName": "CLIENTE"})
    from abc_invoicing.application.invoice_mapper import CompanyProfile, invoice_from_dto
    from abc_invoicing.domain.models import DomainError

    company = CompanyProfile.from_dict(json.loads((ROOT / "tests" / "fixtures" / "company.json").read_text(encoding="utf-8")))
    with pytest.raises(DomainError, match=message):
        invoice_from_dto(build_invoice_dto(form), company)


def test_defaults_describe_each_document_type(server):
    url, _ = server
    with urllib.request.urlopen(url + "/api/defaults") as response:
        docs = {d["code"]: d for d in json.loads(response.read())["identityDocuments"]}
    assert (docs["1"]["maxLength"], docs["1"]["rule"]) == (8, "8 dígitos")
    assert (docs["6"]["maxLength"], docs["6"]["minLength"]) == (11, 11)
    assert docs["-"]["maxLength"] == 0


def test_missing_document_number_returns_422(server):
    url, _ = server
    status, data = _post(url + "/api/generate", _form(customer={"documentType": "6", "legalName": "X"}))
    assert status == 422 and "RUC" in data["error"]
