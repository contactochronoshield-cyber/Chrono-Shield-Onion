from flask import Flask, jsonify, request
import time
import logging
import sys
import ssl
import os
import sqlite3
import threading
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
CPU_ANOMALY_THRESHOLD = 90.0
OFFLINE_THRESHOLD_SECONDS = 30

def get_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS peers (
            node_id TEXT PRIMARY KEY,
            last_seen REAL,
            status TEXT,
            cpu_percent REAL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            node_id TEXT,
            anomaly_type TEXT,
            detail TEXT,
            detected_at REAL
        )
    """)
    conn.commit()
    conn.close()

def log_anomaly(node_id, anomaly_type, detail):
    conn = get_db()
    conn.execute(
        "INSERT INTO anomalies (node_id, anomaly_type, detail, detected_at) VALUES (?, ?, ?, ?)",
        (node_id, anomaly_type, detail, time.time())
    )
    conn.commit()
    conn.close()
    logger.warning(f"ANOMALIA [{anomaly_type}] nodo={node_id}: {detail}")

def offline_watcher():
    known_online = {}
    while True:
        try:
            now = time.time()
            conn = get_db()
            rows = conn.execute("SELECT node_id, last_seen FROM peers").fetchall()
            conn.close()
            for node_id, last_seen in rows:
                is_online = (now - last_seen) < OFFLINE_THRESHOLD_SECONDS
                was_online = known_online.get(node_id, True)
                if was_online and not is_online:
                    log_anomaly(node_id, "PEER_OFFLINE", f"Sin heartbeat por mas de {OFFLINE_THRESHOLD_SECONDS}s")
                known_online[node_id] = is_online
        except Exception as e:
            logger.error(f"Error en offline_watcher: {e}")
        time.sleep(10)

@app.route("/mesh/heartbeat", methods=["POST"])
def heartbeat():
    data = request.get_json(silent=True) or {}
    peer_id = data.get("node_id", "unknown")
    cpu = data.get("cpu_percent")

    if cpu is not None and cpu >= CPU_ANOMALY_THRESHOLD:
        log_anomaly(peer_id, "CPU_HIGH", f"CPU al {cpu}% (umbral: {CPU_ANOMALY_THRESHOLD}%)")

    conn = get_db()
    conn.execute("""
        INSERT INTO peers (node_id, last_seen, status, cpu_percent)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            last_seen=excluded.last_seen,
            status=excluded.status,
            cpu_percent=excluded.cpu_percent
    """, (peer_id, time.time(), data.get("status", "unknown"), cpu))
    conn.commit()
    peer_count = conn.execute("SELECT COUNT(*) FROM peers").fetchone()[0]
    conn.close()
    logger.info(f"Heartbeat recibido de peer: {peer_id}")
    return jsonify({"status": "ACK", "node_id": NODE_ID, "peers_known": peer_count}), 200

@app.route("/mesh/peers", methods=["GET"])
def list_peers():
    now = time.time()
    conn = get_db()
    rows = conn.execute("SELECT node_id, last_seen, status, cpu_percent FROM peers").fetchall()
    conn.close()
    active_peers = {
        r[0]: {"last_seen": r[1], "status": r[2], "cpu_percent": r[3], "online": (now - r[1]) < OFFLINE_THRESHOLD_SECONDS}
        for r in rows
    }
    return jsonify({"node_id": NODE_ID, "peers": active_peers}), 200

@app.route("/mesh/anomalies", methods=["GET"])
def list_anomalies():
    conn = get_db()
    rows = conn.execute(
        "SELECT node_id, anomaly_type, detail, detected_at FROM anomalies ORDER BY detected_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    anomalies = [
        {"node_id": r[0], "type": r[1], "detail": r[2], "detected_at": r[3]}
        for r in rows
    ]
    return jsonify({"node_id": NODE_ID, "anomaly_count": len(anomalies), "anomalies": anomalies}), 200

if __name__ == "__main__":
    init_db()
    ensure_tls_certificates()
    cert_path, key_path, ca_path = "certs/server.crt", "certs/server.key", "certs/ca.crt"

    if not (os.path.exists(cert_path) and os.path.exists(key_path) and os.path.exists(ca_path)):
        logger.critical("Certificados mTLS requeridos para el canal mesh. Abortando arranque.")
        sys.exit(1)

    watcher_thread = threading.Thread(target=offline_watcher, daemon=True)
    watcher_thread.start()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    ssl_context.load_verify_locations(cafile=ca_path)
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    logger.info(f"[+] Canal Mesh mTLS iniciado como nodo: {NODE_ID} (deteccion de anomalias activa)")
    app.run(host="0.0.0.0", port=5443, debug=False, ssl_context=ssl_context)
