"""python -m abc_invoicing.web [--port 8000] [--cert certificado-prueba.pfx] [--no-browser]"""
from __future__ import annotations

import argparse
import webbrowser
from pathlib import Path

from .server import REPO, default_password, load_config, serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Form that generates the signed UBL 2.1 XML.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--company", type=Path, default=REPO / "tests" / "fixtures" / "company.json")
    parser.add_argument("--cert", type=Path, default=REPO / "certificado-prueba.pfx",
                        help="Certificate .pfx; the test one is created if it does not exist")
    parser.add_argument("--password", default=None, help="Certificate password (or ABC_CERT_PASSWORD; default 123456)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open the browser")
    args = parser.parse_args()

    default_cert = args.cert == REPO / "certificado-prueba.pfx"
    config = load_config(args.company, args.cert, args.password or default_password(), create_test_cert=default_cert)
    server = serve(config, port=args.port)
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"XML generator running at {url}  ({config.signer_note})  Ctrl+C to stop.")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
