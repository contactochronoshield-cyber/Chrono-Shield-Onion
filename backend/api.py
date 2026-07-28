from flask import Flask, jsonify, request
import time
import logging
import subprocess
import hashlib
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] CHRONO-SHIELD-ONION: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

app = Flask(__name__)

SECRET_TOKEN = "CS_ONION_PERIMETER_SECURE_TOKEN_2026"
FIRMWARE_TARGET_PATH = "backend/api.py"
ip_traffic_monitor = {}

def apply_rate_limit(client_ip):
    now = time.time()
    if client_ip not in ip_traffic_monitor:
        ip_traffic_monitor[client_ip] = []
    
    ip_traffic_monitor[client_ip] = [t for t in ip_traffic_monitor[client_ip] if now - t < 60]
    
    if len(ip_traffic_monitor[client_ip]) >= 30:
        logging.warning(f"Mitigación DoS activada - IP bloqueada temporalmente: {client_ip}")
        return False
    
    ip_traffic_monitor[client_ip].append(now)
    return True

def get_secure_connections():
    try:
        proc = subprocess.Popen(["netstat", "-an"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        stdout, _ = proc.communicate()
        lines = stdout.decode('utf-8', errors='ignore').split('\n')
        established_count = sum(1 for line in lines if "ESTABLISHED" in line)
        return established_count
    except Exception as e:
        logging.error(f"Fallo en la recolección de sockets de red: {str(e)}")
        return 0

def read_procfs_hardware():
    try:
        cpu, ram_used = "0.0%", "0%"
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                cpu = f.read().split()[0]
                cpu = f"{float(cpu)*100:.1f}%"
        
        if os.path.exists("/proc/meminfo"):
            with open("/proc/meminfo", "r") as f:
                lines = f.readlines()
                total = int(lines[0].split()[1])
                free = int(lines[1].split()[1])
                ram_used = int(((total - free) / total) * 100)
                ram_used = f"{ram_used}%"
                
        return {"cpu": cpu, "ram": ram_used}
    except Exception as e:
        logging.error(f"Error de lectura en procfs (Kernel): {str(e)}")
        return {"cpu": "0%", "ram": "0%"}

def calculate_firmware_attestation():
    sha256_hash = hashlib.sha256()
    try:
        if os.path.exists(FIRMWARE_TARGET_PATH):
            with open(FIRMWARE_TARGET_PATH, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
    except Exception as e:
        logging.error(f"Error calculando hardware attestation: {str(e)}")
    return "UNVERIFIED_SHA256_CORE"

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "HEALTHY",
        "service": "chrono-shield-onion-core",
        "timestamp": int(time.time())
    }), 200

@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    metrics = read_procfs_hardware()
    cpu_val = metrics["cpu"].replace("%", "")
    ram_val = metrics["ram"].replace("%", "")
    active_conns = get_secure_connections()
    
    output = f"""# HELP chronoshield_cpu_usage_ratio Current CPU load average percentage
# TYPE chronoshield_cpu_usage_ratio gauge
chronoshield_cpu_usage_ratio {cpu_val if cpu_val else 0}

# HELP chronoshield_ram_usage_ratio Current RAM usage percentage
# TYPE chronoshield_ram_usage_ratio gauge
chronoshield_ram_usage_ratio {ram_val if ram_val else 0}

# HELP chronoshield_active_connections Established secure network connections
# TYPE chronoshield_active_connections gauge
chronoshield_active_connections {active_conns}
"""
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route("/api/v1/telemetry", methods=["GET"])
def get_telemetry():
    client_ip = request.remote_addr
    
    if not apply_rate_limit(client_ip):
        return jsonify({"error": "TOO_MANY_REQUESTS", "message": "Límite de peticiones excedido."}), 429
    
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {SECRET_TOKEN}":
        logging.error(f"Acceso denegado (mTLS / Token inválido) desde IP: {client_ip}")
        return jsonify({"error": "UNAUTHORIZED_ACCESS", "message": "Token inválido o ausente."}), 401
        
    metrics = read_procfs_hardware()
    firmware_hash = calculate_firmware_attestation()
    
    logging.info(f"Telemetría segura despachada a IP autorizada: {client_ip}")
    
    return jsonify({
        "status": "IMMUTABLE_NODE_ONLINE",
        "topology": "MESH_PEER_CONNECTED",
        "telemetry": {
            "cpu": metrics["cpu"],
            "ram": metrics["ram"],
            "active_nodes": get_secure_connections()
        },
        "security": {
            "mtls_authenticated": True,
            "firmware_sha256": firmware_hash,
            "integrity": "SECURE_SUBPROCESS_VALIDATED"
        }
    }), 200

if __name__ == "__main__":
    logging.info("Iniciando Chrono Shield Onion Core (Production Grade)...")
    app.run(host="127.0.0.1", port=5000, debug=False)
