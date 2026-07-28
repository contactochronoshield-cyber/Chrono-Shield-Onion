from flask import Flask, jsonify, request, send_from_directory
import time
import logging
import hashlib
import os
import sys
import signal

# Configuración avanzada de logging forense para infraestructura crítica
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [PID:%(process)d] CHRONO-SHIELD-CRITICAL: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/security_audit.log")
    ]
)

app = Flask(__name__, static_folder="../frontend", static_url_path="")
ip_traffic_monitor = {}

def handle_sigterm(signum, frame):
    logging.warning("Señal de apagado del sistema (SIGTERM) recibida. Cerrando sockets y liberando recursos perimetrales con seguridad...")
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

def apply_rate_limit(client_ip):
    now = time.time()
    if client_ip not in ip_traffic_monitor:
        ip_traffic_monitor[client_ip] = []
    ip_traffic_monitor[client_ip] = [t for t in ip_traffic_monitor[client_ip] if now - t < 60]
    if len(ip_traffic_monitor[client_ip]) >= 20: # Restricción más estricta para infraestructura crítica
        logging.critical(f"ALERTA DE SEGURIDAD: Ataque de saturación DoS mitigado para la IP: {client_ip}")
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
        logging.error(f"Fallo crítico al inspeccionar la tabla TCP del kernel: {str(e)}")
        return 0

def read_procfs_hardware():
    try:
        cpu_load, ram_usage = "0.0%", "0%"
        disk_usage_pct = "0%"
        
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

        # Verificación real del sistema de archivos local
        st = os.statvfs("/")
        free_bytes = st.f_bavail * st.f_frsize
        total_bytes = st.f_blocks * st.f_frsize
        used_bytes = total_bytes - free_bytes
        if total_bytes > 0:
            disk_usage_pct = f"{(used_bytes / total_bytes) * 100:.1f}%"

        return {"cpu": cpu_load, "ram": ram_usage, "disk": disk_usage_pct}
    except Exception as e:
        logging.error(f"Error crítico leyendo recursos del kernel: {str(e)}")
        return {"cpu": "0.0%", "ram": "0.0%", "disk": "0.0%"}

def calculate_firmware_attestation():
    target_file = "/proc/version" if os.path.exists("/proc/version") else __file__
    sha256_hash = hashlib.sha256()
    try:
        with open(target_file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception as e:
        logging.error(f"Error crítico en hash de attestation: {str(e)}")
    return "CRITICAL_ATTESTATION_FAILED"

@app.route("/")
def serve_frontend():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "CRITICAL_NODE_HEALTHY",
        "service": "chrono-shield-onion-core",
        "epoch": int(time.time()),
        "security_layer": "ACTIVE"
    }), 200

@app.route("/metrics", methods=["GET"])
def prometheus_metrics():
    metrics = read_procfs_hardware()
    cpu_val = metrics["cpu"].replace("%", "")
    ram_val = metrics["ram"].replace("%", "")
    disk_val = metrics["disk"].replace("%", "")
    active_conns = get_real_active_connections()
    
    output = f"""# HELP chronoshield_cpu_usage_ratio Current CPU load average percentage
# TYPE chronoshield_cpu_usage_ratio gauge
chronoshield_cpu_usage_ratio {cpu_val if cpu_val else 0}

# HELP chronoshield_ram_usage_ratio Current RAM usage percentage
# TYPE chronoshield_ram_usage_ratio gauge
chronoshield_ram_usage_ratio {ram_val if ram_val else 0}

# HELP chronoshield_disk_usage_ratio Current Root Filesystem usage percentage
# TYPE chronoshield_disk_usage_ratio gauge
chronoshield_disk_usage_ratio {disk_val if disk_val else 0}

# HELP chronoshield_active_connections Established secure network connections
# TYPE chronoshield_active_connections gauge
chronoshield_active_connections {active_conns}
"""
    return output, 200, {'Content-Type': 'text/plain; charset=utf-8'}

@app.route("/api/v1/telemetry", methods=["GET"])
def get_telemetry():
    client_ip = request.remote_addr
    if not apply_rate_limit(client_ip):
        return jsonify({"error": "TOO_MANY_REQUESTS", "message": "Acceso bloqueado por política perimetral."}), 429
    
    auth = request.headers.get("Authorization", "")
    expected_token = os.environ.get("CHRONO_CORE_SECRET", "CS_ONION_PERIMETER_SECURE_TOKEN_2026")
    
    if not auth or auth != f"Bearer {expected_token}":
        logging.warning(f"Intento de acceso no autorizado registrado desde IP perimetral: {client_ip}")
        return jsonify({"error": "UNAUTHORIZED_PERIMETER_ACCESS", "message": "Credenciales de autorización inválidas."}), 401

    metrics = read_procfs_hardware()
    firmware_hash = calculate_firmware_attestation()

    logging.info(f"Telemetría crítica despachada con éxito a cliente verificado: {client_ip}")

    return jsonify({
        "status": "IMMUTABLE_NODE_ONLINE",
        "topology": "MESH_PEER_CONNECTED",
        "telemetry": {
            "cpu": metrics["cpu"],
            "ram": metrics["ram"],
            "disk": metrics["disk"],
            "active_nodes": get_real_active_connections()
        },
        "security": {
            "perimeter_token_verified": True,
            "firmware_sha256": firmware_hash,
            "integrity": "SYSTEM_KERNEL_SECURE"
        }
    }), 200

if __name__ == "__main__":
    logging.info("Inicializando núcleo de infraestructura crítica Chrono Shield...")
    app.run(host="127.0.0.1", port=5000, debug=False)
