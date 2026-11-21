import argparse
import hashlib
import json
import os
import ssl
import subprocess
import urllib.error
import urllib.request


def _fingerprint(pem):
    return hashlib.sha256(ssl.PEM_cert_to_DER_cert(pem)).hexdigest()


def enroll_node(host, port, token, node_id, ca_sha256, out_dir="certs"):
    os.makedirs(out_dir, mode=0o700, exist_ok=True)
    base = f"https://{host}:{port}"

    # 1. Bajar la CA SIN confiar en ella y validarla contra la huella dada fuera de banda
    insecure = ssl.create_default_context()
    insecure.check_hostname = False
    insecure.verify_mode = ssl.CERT_NONE
    ca_pem = urllib.request.urlopen(base + "/ca.crt", context=insecure, timeout=10).read().decode()
    if _fingerprint(ca_pem) != ca_sha256.replace(":", "").lower():
        raise SystemExit("ERROR: la huella de la CA no coincide. Abortando (posible MITM).")
    ca_path = os.path.join(out_dir, "ca.crt")
    with open(ca_path, "w") as f:
        f.write(ca_pem)

    # 2. Clave privada y CSR generados localmente
    key, csr = os.path.join(out_dir, "node.key"), os.path.join(out_dir, "node.csr")
    subprocess.run(["openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
                    "-keyout", key, "-out", csr, "-subj", f"/CN={node_id}"],
                   check=True, capture_output=True)
    os.chmod(key, 0o600)

    # 3. Enviar token + CSR, ahora SÍ verificando el servidor contra la CA fijada
    ctx = ssl.create_default_context(cafile=ca_path)
    ctx.verify_flags &= ~ssl.VERIFY_X509_STRICT
    body = json.dumps({"token": token, "node_id": node_id,
                       "csr": open(csr).read()}).encode()
    req = urllib.request.Request(base + "/enroll", data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, context=ctx, timeout=20)
    except urllib.error.HTTPError as e:
        raise SystemExit(f"ERROR {e.code}: {e.read().decode()}")
    with open(os.path.join(out_dir, "node.crt"), "w") as f:
        f.write(json.loads(resp.read())["certificate"])
    os.remove(csr)
    print(f"[+] Nodo '{node_id}' enrolado. Certificados en {out_dir}/")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", required=True)
    ap.add_argument("--port", type=int, default=5444)
    ap.add_argument("--token", required=True)
    ap.add_argument("--node-id", required=True)
    ap.add_argument("--ca-sha256", required=True)
    ap.add_argument("--out", default="certs")
    a = ap.parse_args()
    enroll_node(a.host, a.port, a.token, a.node_id, a.ca_sha256, a.out)
