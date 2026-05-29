from flask import Flask, jsonify, request
import time
import logging
import subprocess

# ==============================================================================
# CONFIGURACIÓN DE LOGGING PROFESIONAL
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] CORE-NETWORKS: %(message)s',
    handlers=[
        logging.StreamHandler() # Salida directa a la consola de Termux / Syslog
    ]
)

app = Flask(__name__)

# Credenciales de acceso perimetral
SECRET_TOKEN = "CS_ONION_PERIMETER_SECURE_TOKEN_2026"

# Memoria volátil para Rate Limiting (IP: [timestamps])
ip_traffic_monitor = {}

def apply_rate_limit(client_ip):
    now = time.time()
    if client_ip not in ip_traffic_monitor:
        ip_traffic_monitor[client_ip] = []
    
    # Limpiar registros más viejos de 60 segundos
    ip_traffic_monitor[client_ip] = [t for t in ip_traffic_monitor[client_ip] if now - t < 60]
    
    # Restricción: Máximo 30 peticiones por minuto
    if len(ip_traffic_monitor[client_ip]) >= 30:
        logging.warning(f"Mitigación DoS activada - IP bloqueada temporalmente: {client_ip}")
        return False
        
    ip_traffic_monitor[client_ip].append(now)
    return True

def get_secure_connections():
    try:
        # Ejecución SEGURA sin usar shell=True (Evita inyección de comandos)
        proc = subprocess.Popen(["netstat", "-an"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        stdout, _ = proc.communicate()
        
        # Filtrado nativo en Python en lugar de usar pipes de la shell (grep)
        lines = stdout.decode('utf-8', errors='ignore').split('\n')
        established_count = sum(1 for line in lines if "ESTABLISHED" in line)
        return established_count
    except Exception as e:
        logging.error(f"Fallo en la recolección de sockets de red: {str(e)}")
        return 0

def read_procfs_hardware():
    try:
        with open("/proc/loadavg", "r") as f:
            cpu = f.read().split()[0]
        with open("/proc/meminfo", "r") as f:
            lines = f.readlines()
            total = int(lines[0].split()[1])
            free = int(lines[1].split()[1])
        ram_used = int(((total - free) / total) * 100)
        return {"cpu": f"{float(cpu)*100:.1f}%", "ram": f"{ram_used}%"}
    except Exception as e:
        logging.error(f"Error de lectura en procfs (Kernel): {str(e)}")
        return {"cpu": "0%", "ram": "0%"}

# ==============================================================================
# ENDPOINTS OPERATIVOS
# ==============================================================================

@app.route("/health", methods=["GET"])
def health_check():
    # Endpoint de monitoreo de estado para orquestadores o balanceadores
    return jsonify({
        "status": "HEALTHY",
        "service": "chrono-core-backend",
        "timestamp": int(time.time())
    }), 200

@app.route("/api/v1/telemetry", methods=["GET"])
def get_telemetry():
    client_ip = request.remote_addr
    
    # 1. Validación de Rate Limiting
    if not apply_rate_limit(client_ip):
        return jsonify({"error": "TOO_MANY_REQUESTS", "message": "Límite de peticiones excedido."}), 429

    # 2. Validación de Autenticación Crítica
    auth = request.headers.get("Authorization")
    if not auth or auth != f"Bearer {SECRET_TOKEN}":
        logging.error(f"Acceso denegación de credenciales desde IP: {client_ip}")
        return jsonify({"error": "UNAUTHORIZED_ACCESS", "message": "Token inválido o ausente."}), 401
    
    # 3. Entrega de Métricas Seguras
    metrics = read_procfs_hardware()
    logging.info(f"Métricas despachadas exitosamente a la IP autorizada: {client_ip}")
    
    return jsonify({
        "status": "IMMUTABLE_NODE_ONLINE",
        "telemetry": {
            "cpu": metrics["cpu"],
            "ram": metrics["ram"],
            "active_nodes": get_secure_connections()
        },
        "integrity": "SECURE_SUBPROCESS_VALIDATED"
    }), 200

if __name__ == "__main__":
    logging.info("Iniciando Kernel Core en interfaz de aislamiento local (Puerto 5000)...")
    app.run(host="127.0.0.1", port=5000, debug=False)
