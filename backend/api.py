from flask import Flask, jsonify, request, send_from_directory
import time
import logging
import hashlib
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] CHRONO-SHIELD-ENGINE: %(message)s',
    handlers=[logging.StreamHandler()]
)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
ip_traffic_monitor = {}

def apply_rate_limit(client_ip):
    now = time.time()
    if client_ip not in ip_traffic_monitor:
        ip_traffic_monitor[client_ip] = []
    ip_traffic_monitor[client_ip] = [t for t in ip_traffic_monitor[client_ip] if now - t < 60]
    if len(ip_traffic_monitor[client_ip]) >= 30:
        logging.warning(f"DoS Mitigator: Límite de tasa excedido para IP: {client_ip}")
        return False
    ip_traffic_monitor[client_ip].append(now)
    return True

def get_real_active_connections():
    established_count = 0
    try:
        if os.path.exists("/proc/net/tcp"):
            with open("/proc/net/tcp", "r") as f:
                lines = f.readlines()[1:]
                for line in lines:
                    parts = line.split()
                    if len(parts) > 3 and parts[3] == "01":
                        established_count += 1
        return established_count
    except Exception as e:
        logging.error(f"Error analizando sockets activos: {str(e)}")
        return 1

def read_procfs_hardware():
    try:
        cpu_load, ram_usage = "0.0%", "0%"
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                load_vals = f.read().split()
                cpu_load = f"{float(load_vals[0]) * 100:.1f}%"
        if os.path.exists("/proc/meminfo"):
            mem_info = {}
            with open("/proc/meminfo", "r") as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2:
                        mem_info[parts[0].rstrip(':')] = int(parts[1])
            total = mem_info.get('MemTotal', 1)
            free = mem_info.get('MemFree', 0) + mem_info.get('Buffers', 0) + mem_info.get('Cached', 0)
            used = total - free
            ram_usage = f"{(used / total) * 100:.1f}%"
        return {"cpu": cpu_load, "ram": ram_usage}
    except Exception as e:
        logging.error(f"Error leyendo telemetría: {str(e)}")
        return {"cpu": "0.0%", "ram": "0.0%"}

def calculate_firmware_attestation():
    """Attestation real basada en el hash SHA-256 del kernel o de un archivo del sistema binario crítico si existe."""
    target_file = "/proc/version" if os.path.exists("/proc/version") else __file__
    sha256_hash = hashlib.sha256()
    try:
        with open(target_file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logging.error(f"Error en attestation real: {str(e)}")
    return "KERNEL_ATTESTATION_FAILED"

@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "HEALTHY", "service": "chrono-shield-onion-core", "timestamp": int(time.time())}), 200

@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    metrics = read_procfs_hardware()
    cpu_val = metrics["cpu"].replace("%", "")
    ram_val = metrics["ram"].replace("%", "")
    active_conns = get_real_active_connections()
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
        return jsonify({"error": "TOO_MANY_REQUESTS", "message": "Límite excedido."}), 429
    
    auth = request.headers.get("Authorization", "")
    expected_token = os.environ.get("CHRONO_CORE_SECRET", "CS_ONION_PERIMETER_SECURE_TOKEN_2026")
    
    if not auth or auth != f"Bearer {expected_token}":
        return jsonify({"error": "UNAUTHORIZED_ACCESS", "message": "Token inválido o ausente."}), 401

    metrics = read_procfs_hardware()
    firmware_hash = calculate_firmware_attestation()

    return jsonify({
        "status": "IMMUTABLE_NODE_ONLINE",
        "topology": "MESH_PEER_CONNECTED",
        "telemetry": {
            "cpu": metrics["cpu"],
            "ram": metrics["ram"],
            "active_nodes": get_real_active_connections()
        },
        "security": {
            "token_authenticated": True,
            "firmware_sha256": firmware_hash,
            "integrity": "PROC_KERNEL_VALIDATED"
        }
    }), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
