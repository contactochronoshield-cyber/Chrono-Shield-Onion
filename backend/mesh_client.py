import subprocess
import time
import os
import sys
import requests
import psutil

def _safe_cpu():
    try:
        return psutil.cpu_percent(interval=1)
    except Exception:
        return -1.0

NODE_ID = os.environ.get("CHRONO_NODE_ID")
NODE_LOCATION = os.environ.get("CHRONO_NODE_LOCATION", "ubicacion-no-especificada")
MAIN_NODE_HOST = os.environ.get("CHRONO_MAIN_NODE", "127.0.0.1")
CERT_DIR = "peer_certs"

if not NODE_ID:
    print("CHRONO_NODE_ID no definido. Aborta.")
    sys.exit(1)

os.makedirs(CERT_DIR, exist_ok=True)
key_path = f"{CERT_DIR}/{NODE_ID}.key"
crt_path = f"{CERT_DIR}/{NODE_ID}.crt"
csr_path = f"{CERT_DIR}/{NODE_ID}.csr"
ca_crt = "certs/ca.crt"
ca_key = "certs/ca.key"

if not os.path.exists(crt_path):
    print(f"[+] Generando certificado propio para {NODE_ID}...")
    subprocess.run(["openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
        "-keyout", key_path, "-out", csr_path, "-subj", f"/CN={NODE_ID}"], check=True)
    subprocess.run(["openssl", "x509", "-req", "-days", "365",
        "-in", csr_path, "-CA", ca_crt, "-CAkey", ca_key,
        "-set_serial", str(int(time.time())), "-out", crt_path], check=True)
    print(f"[+] Certificado generado: {crt_path}")

url = f"https://{MAIN_NODE_HOST}:5443/mesh/heartbeat"
cert = (crt_path, key_path)

print(f"[+] Iniciando heartbeat de {NODE_ID} hacia {MAIN_NODE_HOST}...")
while True:
    try:
        payload = {
            "node_id": NODE_ID,
            "status": "online",
            "location": NODE_LOCATION,
            "cpu_percent": _safe_cpu()
        }
        r = requests.post(url, json=payload, cert=cert, verify=ca_crt, timeout=5)
        print(f"[{time.ctime()}] Heartbeat enviado: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[{time.ctime()}] Fallo de heartbeat: {e}")
    time.sleep(15)
