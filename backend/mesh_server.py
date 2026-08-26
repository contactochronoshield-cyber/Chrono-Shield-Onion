from flask import Flask, jsonify, request
import time
import logging
import sys
import ssl
import os
import sqlite3
from security.crypto import ensure_tls_certificates

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ChronoMeshChannel")

app = Flask(__name__)
NODE_ID = os.environ.get("CHRONO_NODE_ID", "chrono-node-unnamed")
DB_PATH = "mesh_peers.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS peers (
            node_id TEXT PRIMARY KEY,
            last_seen REAL,
            status TEXT,
            cpu_percent REAL
        )
    """)
    conn.commit()
    conn.close()

@app.route("/mesh/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json(silent=True) or {}
    peer_id = data.get("node_id", "unknown")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO peers (node_id, last_seen, status, cpu_percent)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            last_seen=excluded.last_seen,
            status=excluded.status,
            cpu_percent=excluded.cpu_percent
    """, (peer_id, time.time(), data.get("status", "unknown"), data.get("cpu_percent")))
    conn.commit()
    peer_count = conn.execute("SELECT COUNT(*) FROM peers").fetchone()[0]
    conn.close()
    logger.info(f"Heartbeat recibido de peer: {peer_id}")
    return jsonify({"status": "ACK", "node_id": NODE_ID, "peers_known": peer_count}), 200

@app.route("/mesh/peers", methods=["GET"])
def list_peers():
    now = time.time()
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT node_id, last_seen, status, cpu_percent FROM peers").fetchall()
    conn.close()
    active_peers = {
        r[0]: {"last_seen": r[1], "status": r[2], "cpu_percent": r[3], "online": (now - r[1]) < 30}
        for r in rows
    }
    return jsonify({"node_id": NODE_ID, "peers": active_peers}), 200

if __name__ == "__main__":
    init_db()
    ensure_tls_certificates()
    cert_path, key_path, ca_path = "certs/server.crt", "certs/server.key", "certs/ca.crt"

    if not (os.path.exists(cert_path) and os.path.exists(key_path) and os.path.exists(ca_path)):
        logger.critical("Certificados mTLS requeridos para el canal mesh. Abortando arranque.")
        sys.exit(1)

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    ssl_context.load_verify_locations(cafile=ca_path)
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    logger.info(f"[+] Canal Mesh mTLS iniciado como nodo: {NODE_ID} (persistencia SQLite activa)")
    app.run(host="0.0.0.0", port=5443, debug=False, ssl_context=ssl_context)
