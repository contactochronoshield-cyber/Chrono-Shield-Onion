import os
import sys
import time

import psutil
import requests

try:
    from backend.enroll_client import enroll_node
except ImportError:
    from enroll_client import enroll_node


def _safe_cpu():
    try:
        return psutil.cpu_percent(interval=1)
    except Exception:
        return -1.0


NODE_ID = os.environ.get("CHRONO_NODE_ID")
NODE_LOCATION = os.environ.get("CHRONO_NODE_LOCATION", "ubicacion-no-especificada")
MAIN_NODE_HOST = os.environ.get("CHRONO_MAIN_NODE", "127.0.0.1")
ENROLL_PORT = int(os.environ.get("CHRONO_ENROLL_PORT", "5444"))
CERT_DIR = "peer_certs"

if not NODE_ID:
    print("CHRONO_NODE_ID no definido. Aborta.")
    sys.exit(1)

crt_path = os.path.join(CERT_DIR, "node.crt")
key_path = os.path.join(CERT_DIR, "node.key")
ca_crt = os.path.join(CERT_DIR, "ca.crt")

if not os.path.exists(crt_path):
    token = os.environ.get("CHRONO_ENROLL_TOKEN")
    ca_sha = os.environ.get("CHRONO_CA_SHA256")
    if not token or not ca_sha:
        print("Nodo sin certificado. Define CHRONO_ENROLL_TOKEN y CHRONO_CA_SHA256 "
              "(los entrega el operador del nodo principal). Aborta.")
        sys.exit(1)
    print(f"[+] Enrolando {NODE_ID} en {MAIN_NODE_HOST}:{ENROLL_PORT}...")
    enroll_node(MAIN_NODE_HOST, ENROLL_PORT, token, NODE_ID, ca_sha, CERT_DIR)

url = f"https://{MAIN_NODE_HOST}:5443/mesh/heartbeat"
cert = (crt_path, key_path)

print(f"[+] Iniciando heartbeat de {NODE_ID} hacia {MAIN_NODE_HOST}...")
while True:
    try:
        payload = {
            "node_id": NODE_ID,
            "status": "online",
            "location": NODE_LOCATION,
            "cpu_percent": _safe_cpu(),
        }
        r = requests.post(url, json=payload, cert=cert, verify=ca_crt, timeout=5)
        print(f"[{time.ctime()}] Heartbeat enviado: {r.status_code} - {r.text}")
    except Exception as e:
        print(f"[{time.ctime()}] Fallo de heartbeat: {e}")
    time.sleep(15)
