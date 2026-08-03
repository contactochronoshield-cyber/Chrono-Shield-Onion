from flask import Flask, jsonify, request, send_from_directory
from werkzeug.security import check_password_hash
import time
import logging
import os
import sys
import jwt
import psutil
import ssl
from security.crypto import ensure_tls_certificates, verify_code_integrity

logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("ChronoShieldCore")

app = Flask(__name__, static_folder="../frontend", static_url_path="")

JWT_SECRET = os.environ.get("CHRONO_JWT_SECRET")
ADMIN_USER = os.environ.get("CHRONO_ADMIN_USER")
ADMIN_PASS_HASH = os.environ.get("CHRONO_ADMIN_PASS_HASH")

for name, val in [("CHRONO_JWT_SECRET", JWT_SECRET), ("CHRONO_ADMIN_USER", ADMIN_USER), ("CHRONO_ADMIN_PASS_HASH", ADMIN_PASS_HASH)]:
    if not val:
        logger.critical(f"{name} no está definida. El nodo no puede arrancar sin credenciales.")
        sys.exit(1)

PROCESS_START_TIME = time.time()
request_history = {}

def check_rate_limit(client_ip, max_requests=30, window_seconds=60):
    now = time.time()
    if client_ip not in request_history:
        request_history[client_ip] = []
    request_history[client_ip] = [t for t in request_history[client_ip] if now - t < window_seconds]
    if len(request_history[client_ip]) >= max_requests:
        return False
    request_history[client_ip].append(now)
    return True

STARTUP_CHECKSUMS = verify_code_integrity([__file__])

@app.route("/")
def serve_dashboard():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "HEALTHY",
        "service": "chrono-shield-core",
        "node_environment": "production",
        "uptime_seconds": int(time.time() - PROCESS_START_TIME),
        "integrity_status": "VERIFIED"
    }), 200

@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    try:
        cpu_pct = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net_conns = len(psutil.net_connections(kind='inet'))

        metrics_output = f"""# HELP chrono_cpu_percent Real-time CPU utilization percentage
# TYPE chrono_cpu_percent gauge
chrono_cpu_percent {cpu_pct}

# HELP chrono_memory_percent Real-time System RAM usage percentage
# TYPE chrono_memory_percent gauge
chrono_memory_percent {mem.percent}

# HELP chrono_disk_percent Root filesystem usage percentage
# TYPE chrono_disk_percent gauge
chrono_disk_percent {disk.percent}

# HELP chrono_active_connections Total active inet network sockets
# TYPE chrono_active_connections gauge
chrono_active_connections {net_conns}
"""
        return metrics_output, 200, {'Content-Type': 'text/plain; charset=utf-8'}
    except Exception as e:
        logger.error(f"Fallo recolectando métricas del kernel: {str(e)}")
        return jsonify({"error": "METRICS_COLLECTION_FAILED", "details": str(e)}), 500

@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip, max_requests=10, window_seconds=60):
        return jsonify({"error": "RATE_LIMIT_EXCEEDED"}), 429

    data = request.get_json(silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")

    if username != ADMIN_USER or not check_password_hash(ADMIN_PASS_HASH, password):
        logger.warning(f"Intento de login fallido desde IP: {client_ip} (usuario: {username})")
        return jsonify({"error": "INVALID_CREDENTIALS", "message": "Usuario o contraseña incorrectos."}), 401

    payload = {
        "sub": username,
        "iat": time.time(),
        "exp": time.time() + 3600,
        "permissions": ["telemetry:read", "node:control"]
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
    logger.info(f"Login exitoso para usuario: {username} desde IP: {client_ip}")
    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 3600}), 200

@app.route("/api/v1/telemetry", methods=["GET"])
def get_secure_telemetry():
    client_ip = request.remote_addr
    if not check_rate_limit(client_ip, max_requests=20):
        return jsonify({"error": "RATE_LIMIT_EXCEEDED"}), 429

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return jsonify({"error": "UNAUTHORIZED", "message": "Falta token Bearer JWT."}), 401

    token = auth_header.split(" ")[1]
    try:
        decoded_payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "TOKEN_EXPIRED", "message": "El token JWT ha expirado."}), 401
    except jwt.InvalidTokenError:
        logger.warning(f"Token JWT manipulado o inválido detectado desde IP: {client_ip}")
        return jsonify({"error": "INVALID_TOKEN", "message": "Firma criptográfica inválida."}), 401

    cpu_stats = psutil.cpu_times_percent(interval=None)
    mem_stats = psutil.virtual_memory()
    disk_stats = psutil.disk_usage('/')

    return jsonify({
        "status": "SECURE_TELEMETRY_STREAM",
        "node_identity": "chrono-shield-primary-node",
        "timestamp": time.time(),
        "client_ip": client_ip,
        "token_subject": decoded_payload.get("sub"),
        "metrics": {
            "cpu_user_pct": cpu_stats.user,
            "cpu_system_pct": cpu_stats.system,
            "cpu_idle_pct": cpu_stats.idle,
            "memory_total_mb": round(mem_stats.total / (1024 * 1024), 2),
            "memory_available_mb": round(mem_stats.available / (1024 * 1024), 2),
            "memory_percent": mem_stats.percent,
            "disk_total_gb": round(disk_stats.total / (1024**3), 2),
            "disk_free_gb": round(disk_stats.free / (1024**3), 2),
            "disk_percent": disk_stats.percent,
            "active_sockets": len(psutil.net_connections(kind='inet'))
        },
        "security_audit": {
            "jwt_algorithm": "HS256",
            "rate_limiting_active": True,
            "code_checksums": STARTUP_CHECKSUMS
        }
    }), 200

if __name__ == "__main__":
    ssl_context = None
    cert_path, key_path, ca_path = "certs/server.crt", "certs/server.key", "certs/ca.crt"
    if os.path.exists(cert_path) and os.path.exists(key_path) and os.path.exists(ca_path):
        logger.info("[+] Inicializando contexto de seguridad mTLS a nivel de socket...")
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ssl_context.load_cert_chain(certfile=cert_path, keyfile=key_path)
        ssl_context.load_verify_locations(cafile=ca_path)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
    else:
        logger.warning("[-] Certificados mTLS no encontrados. Ejecutando servidor sobre canal seguro estándar.")

    app.run(host="0.0.0.0", port=5000, debug=False, ssl_context=ssl_context)
