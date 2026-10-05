import sys
import json
import base64
import subprocess
import requests

def verify(host, port=5443, ca_cert="backend/certs/ca.crt", client_cert=None, client_key=None):
    url = f"https://{host}:{port}/mesh/canary"
    cert = (client_cert, client_key) if client_cert and client_key else None
    r = requests.get(url, verify=ca_cert, cert=cert, timeout=5)
    data = r.json()

    statement_json = json.dumps(data["statement"], sort_keys=True)
    with open("/tmp_canary_verify.json", "w") as f:
        f.write(statement_json)
    with open("/tmp_canary_verify.sig", "wb") as f:
        f.write(base64.b64decode(data["signature_b64"]))
    with open("/tmp_canary_pub.pem", "w") as f:
        f.write(data["public_key_pem"])

    result = subprocess.run(
        ["openssl", "dgst", "-sha256", "-verify", "/tmp_canary_pub.pem",
         "-signature", "/tmp_canary_verify.sig", "/tmp_canary_verify.json"],
        capture_output=True, text=True
    )
    print(f"Firma valida: {'SI' if 'OK' in result.stdout else 'NO'}")
    print(f"Declaracion: {data['statement']['declaration']}")
    print(f"Nodo: {data['statement']['node_id']}")
    print(f"Publicado: {data['published_at']}")

if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    verify(host)
