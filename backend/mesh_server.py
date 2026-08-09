from flask import Flask, jsonify, request
import time
import logging
import sys
import ssl
import os
from security.crypto import ensure_tls_certificates

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ChronoMeshChannel")

app = Flask(__name__)

NODE_ID = os.environ.get("CHRONO_NODE_ID", "chrono-node-unnamed")
known_peers = {}

@app.route("/mesh/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json(silent=True) or {}
    peer_id = data.get("node_id", "unknown")
    known_peers[peer_id] = {
        "last_seen": time.time(),
        "status": data.get("status", "unknown"),
        "cpu_percent": data.get("cpu_percent"),
    }
    logger.info(f"Heartbeat recibido de peer: {peer_id}")
    return jsonify({"status": "ACK", "node_id": NODE_ID, "peers_known": len(known_peers)}), 200

@app.route("/mesh/peers", methods=["GET"])
def list_peers():
    now = time.time()
    active_peers = {pid: p for pid, p in known_peers.items() if now - p["last_seen"] < 30}
    return jsonify({"node_id": NODE_ID, "active_peers": active_peers}), 200

if __name__ == "__main__":
    ensure_tls_certificates()
    cert_path, key_path, ca_path = "certs/server.crt", "certs/server.key", "certs/ca.crt"

    if not (os.path.exists(cert_path) and os.path.exists(key_path) and os.path.exists(ca_path)):
        logger.critical("Certificados mTLS requeridos para el canal mesh. Abortando arranque.")
        sys.exit(1)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    ssl_context.load_verify_locations(cafile=ca_path)
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    logger.info(f"[+] Canal Mesh mTLS iniciado como nodo: {NODE_ID}")
    app.run(host="0.0.0.0", port=5443, debug=False, ssl_context=ssl_context)
