"""Verifica el warrant canary de un nodo Chrono-Shield-Onion.
Uso: python backend/verify_canary.py HOST [--port 5444] [--pin SHA256_DE_LA_CLAVE_PUBLICA]
Por defecto usa el endpoint público /canary (5444, sin certificado de cliente)."""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile


def pubkey_fingerprint(public_key_pem):
    der = subprocess.run(["openssl", "pkey", "-pubin", "-outform", "DER"],
                         input=public_key_pem.encode(), capture_output=True, check=True).stdout
    return hashlib.sha256(der).hexdigest()


def verify_data(data, pin=None):
    """Devuelve (firma_valida, pin_coincide|None, huella_clave_publica)."""
    statement_json = json.dumps(data["statement"], sort_keys=True)
    sig = base64.b64decode(data["signature_b64"])
    with tempfile.TemporaryDirectory() as d:
        paths = {n: os.path.join(d, n) for n in ("stmt.json", "stmt.sig", "pub.pem")}
        open(paths["stmt.json"], "w").write(statement_json)
        open(paths["stmt.sig"], "wb").write(sig)
        open(paths["pub.pem"], "w").write(data["public_key_pem"])
        r = subprocess.run(["openssl", "dgst", "-sha256", "-verify", paths["pub.pem"],
                            "-signature", paths["stmt.sig"], paths["stmt.json"]],
                           capture_output=True, text=True)
    fp = pubkey_fingerprint(data["public_key_pem"])
    pinned = None if not pin else (fp == pin.replace(":", "").lower())
    return ("OK" in r.stdout), pinned, fp


def verify(host, port=5444, pin=None, ca_cert=None, client_cert=None, client_key=None):
    import requests
    path = "/mesh/canary" if client_cert else "/canary"
    cert = (client_cert, client_key) if client_cert and client_key else None
    # La firma, no el TLS, es lo que prueba la integridad; TLS solo protege el transporte.
    r = requests.get(f"https://{host}:{port}{path}", verify=ca_cert or False, cert=cert, timeout=5)
    data = r.json()
    ok, pinned, fp = verify_data(data, pin)
    print(f"Firma valida: {'SI' if ok else 'NO'}")
    print(f"Huella clave publica (SHA-256): {fp}")
    if pin:
        print(f"Coincide con el pin: {'SI' if pinned else 'NO  <-- ¡CLAVE DISTINTA A LA ESPERADA!'}")
    else:
        print("Aviso: sin --pin, la clave publica la entrega el propio servidor.")
    print(f"Declaracion: {data['statement']['declaration']}")
    print(f"Nodo: {data['statement']['node_id']}")
    print(f"Publicado: {data['published_at']}")
    return ok and (pinned is not False)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("host", nargs="?", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5444)
    ap.add_argument("--pin")
    ap.add_argument("--ca")
    ap.add_argument("--client-cert")
    ap.add_argument("--client-key")
    a = ap.parse_args()
    sys.exit(0 if verify(a.host, a.port, a.pin, a.ca, a.client_cert, a.client_key) else 1)
