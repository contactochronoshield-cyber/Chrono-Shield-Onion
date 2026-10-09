from flask import Flask, jsonify, request
import time
import logging
import sys
import ssl
import os
import sqlite3
import threading
from security.crypto import ensure_tls_certificates
from security.config_integrity import check_integrity, establish_baseline
from security.canary import publish_canary, get_latest_canary
from security.alert_dispatcher import send_alert

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
MAINTENANCE_UNTIL = {"timestamp": 0}
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
            cpu_percent REAL,
            location TEXT
        )
    """)
    try:
        conn.execute("ALTER TABLE peers ADD COLUMN location TEXT")
    except Exception:
        pass
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

def get_node_location(node_id):
    try:
        conn = get_db()
        row = conn.execute("SELECT location FROM peers WHERE node_id = ?", (node_id,)).fetchone()
        conn.close()
        return row[0] if row and row[0] else None
    except Exception:
        return None

def log_anomaly(node_id, anomaly_type, detail):
    loc = get_node_location(node_id)
    if loc:
        detail = f"[{loc}] {detail}"
    conn = get_db()
    conn.execute(
        "INSERT INTO anomalies (node_id, anomaly_type, detail, detected_at) VALUES (?, ?, ?, ?)",
        (node_id, anomaly_type, detail, time.time())
    )
    conn.commit()
    conn.close()
    logger.warning(f"ANOMALIA [{anomaly_type}] nodo={node_id}: {detail}")
    send_alert(f"[{anomaly_type}] nodo={node_id}: {detail}")

def config_watcher():
    while True:
        try:
            changes = check_integrity()
            if changes:
                if time.time() < MAINTENANCE_UNTIL["timestamp"]:
                    logger.info(f"Cambio de config detectado DURANTE ventana de mantenimiento autorizada, omitiendo alerta")
                else:
                    for c in changes:
                        log_anomaly(NODE_ID, "CONFIG_TAMPERED", f"Archivo modificado sin autorizacion: {c['path']}")
                establish_baseline()
        except Exception as e:
            logger.error(f"Error en config_watcher: {e}")
        time.sleep(30)

CORRELATION_WINDOW_SECONDS = 120
CORRELATION_MIN_NODES = 2

CANARY_INTERVAL_SECONDS = 60

def canary_publisher():
    while True:
        try:
            publish_canary(NODE_ID)
            logger.info("Warrant canary publicado y firmado")
        except Exception as e:
            logger.error(f"Error publicando canary: {e}")
        time.sleep(CANARY_INTERVAL_SECONDS)

def correlation_watcher():
    seen_correlations = set()
    while True:
        try:
            now = time.time()
            conn = get_db()
            rows = conn.execute(
                "SELECT node_id, anomaly_type, detected_at FROM anomalies WHERE detected_at > ? AND anomaly_type != 'COORDINATED_PATTERN'",
                (now - CORRELATION_WINDOW_SECONDS,)
            ).fetchall()
            conn.close()

            by_type = {}
            for node_id, atype, detected_at in rows:
                by_type.setdefault(atype, set()).add(node_id)

            for atype, nodes in by_type.items():
                if len(nodes) >= CORRELATION_MIN_NODES:
                    key = (atype, tuple(sorted(nodes)))
                    if key not in seen_correlations:
                        seen_correlations.add(key)
                        detail = f"Mismo tipo de anomalia ({atype}) en {len(nodes)} nodos distintos en {CORRELATION_WINDOW_SECONDS}s: {sorted(nodes)}"
                        log_anomaly("MESH_WIDE", "COORDINATED_PATTERN", detail)
        except Exception as e:
            logger.error(f"Error en correlation_watcher: {e}")
        time.sleep(15)

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
    location = data.get("location", "desconocida")
    conn.execute("""
        INSERT INTO peers (node_id, last_seen, status, cpu_percent, location)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            last_seen=excluded.last_seen,
            status=excluded.status,
            cpu_percent=excluded.cpu_percent,
            location=excluded.location
    """, (peer_id, time.time(), data.get("status", "unknown"), cpu, location))
    conn.commit()
    peer_count = conn.execute("SELECT COUNT(*) FROM peers").fetchone()[0]
    conn.close()
    logger.info(f"Heartbeat recibido de peer: {peer_id}")
    return jsonify({"status": "ACK", "node_id": NODE_ID, "peers_known": peer_count}), 200

@app.route("/mesh/maintenance", methods=["POST"])
def start_maintenance():
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "UNAUTHORIZED", "message": "Requiere token JWT de administrador (mismo que el dashboard)."}), 401

    token = auth_header.split(" ")[1]
    import jwt as jwt_lib
    jwt_secret = os.environ.get("CHRONO_JWT_SECRET")
    try:
        jwt_lib.decode(token, jwt_secret, algorithms=["HS256"])
    except Exception:
        return jsonify({"error": "INVALID_TOKEN"}), 401

    data = request.get_json(silent=True) or {}
    minutes = min(data.get("minutes", 10), 60)
    MAINTENANCE_UNTIL["timestamp"] = time.time() + (minutes * 60)
    logger.warning(f"Ventana de mantenimiento activada por {minutes} minutos (autenticado)")
    return jsonify({"status": "MAINTENANCE_ACTIVE", "until": MAINTENANCE_UNTIL["timestamp"]}), 200

@app.route("/mesh/canary", methods=["GET"])
def canary_endpoint():
    data = get_latest_canary()
    if not data:
        return jsonify({"error": "NO_CANARY_PUBLISHED_YET"}), 404
    return jsonify(data), 200

@app.route("/mesh/peers", methods=["GET"])
def list_peers():
    now = time.time()
    conn = get_db()
    rows = conn.execute("SELECT node_id, last_seen, status, cpu_percent, location FROM peers").fetchall()
    conn.close()
    active_peers = {
        r[0]: {"last_seen": r[1], "status": r[2], "cpu_percent": r[3], "location": r[4], "online": (now - r[1]) < OFFLINE_THRESHOLD_SECONDS}
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

    establish_baseline()
    watcher_thread = threading.Thread(target=offline_watcher, daemon=True)
    watcher_thread.start()
    config_thread = threading.Thread(target=config_watcher, daemon=True)
    config_thread.start()
    correlation_thread = threading.Thread(target=correlation_watcher, daemon=True)
    correlation_thread.start()
    canary_thread = threading.Thread(target=canary_publisher, daemon=True)
    canary_thread.start()

    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
    ssl_context.load_verify_locations(cafile=ca_path)
    ssl_context.verify_mode = ssl.CERT_REQUIRED

    logger.info(f"[+] Canal Mesh mTLS iniciado como nodo: {NODE_ID} (deteccion de anomalias activa)")
    app.run(host="0.0.0.0", port=5443, debug=False, ssl_context=ssl_context)
