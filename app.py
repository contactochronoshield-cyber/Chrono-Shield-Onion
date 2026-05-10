from flask import Flask, render_template, request, jsonify
import subprocess
import sqlite3
from datetime import datetime
import re

# --- CONFIGURACIÓN ESTRATÉGICA CHRONO SHIELD ---
app = Flask(__name__)

# Estado del Blindaje (Protocolo de Defensa)
modo_blindado = False
ip_autorizada = "127.0.0.1"

# --- NÚCLEO DE DATOS (SQLite) ---
def init_db():
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    # Registramos: Fecha, Identidad, Evento e IP de origen
    cursor.execute('''CREATE TABLE IF NOT EXISTS logs 
                      (fecha TEXT, usuario TEXT, estado TEXT, ip TEXT)''')
    conn.commit()
    conn.close()

# Inicializamos la DB al arrancar
init_db()

# --- MIDDLEWARE DE SEGURIDAD (EL ESCUDO) ---
@app.before_request
def verificar_blindaje():
    global modo_blindado
    # Si el blindaje está ON, solo el CEO (localhost) puede entrar
    if modo_blindado:
        if request.remote_addr not in [ip_autorizada, "192.168.1.15"]:
            return "<h1 style='color:cyan; background:black; text-align:center; padding:50px;'>" \
                   "ACCESO DENEGADO: CHRONO SHIELD ACTIVE (PROTOCOLO BOGOTÁ)</h1>", 403

# --- RUTAS DE MANDO ---

@app.route('/')
def index():
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM logs ORDER BY fecha DESC LIMIT 10")
    logs = cursor.fetchall()
    
    # Intentamos obtener el último conteo de dispositivos
    cursor.execute("SELECT estado FROM logs WHERE usuario='AUDITOR' ORDER BY fecha DESC LIMIT 1")
    ultimo_log = cursor.fetchone()
    num_dispositivos = 0
    if ultimo_log:
        match = re.search(r'\d+', ultimo_log[0])
        if match: num_dispositivos = match.group()

    stats = {
        "usuarios": num_dispositivos,
        "motor": "NMAP TACTICAL",
        "status": "LOCKDOWN" if modo_blindado else "NORMAL",
        "ceo": "DANIEL GONZALES"
    }
    conn.close()
    return render_template('index.html', logs=logs, stats=stats)

@app.route('/ejecutar', methods=['POST'])
def ejecutar():
    ahora = datetime.now().strftime("%H:%M:%S")
    try:
        # Escaneo de red local (Asegúrate de tener nmap instalado: pkg install nmap)
        output = subprocess.check_output(['nmap', '-sn', '192.168.1.0/24'], text=True)
        vivos = len(re.findall(r"Host is up", output))
        msg = f"Auditoría: {vivos} dispositivos identificados en red."
    except Exception as e:
        msg = "Error: Motor Nmap no detectado o sin permisos."

    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (fecha, usuario, estado, ip) VALUES (?, ?, ?, ?)",
                   (ahora, "AUDITOR", msg, "GATEWAY_SCAN"))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": msg})

@app.route('/bloqueo', methods=['POST'])
def bloqueo():
    global modo_blindado
    ahora = datetime.now().strftime("%H:%M:%S")
    modo_blindado = True
    
    msg = "SISTEMA BLINDADO: Bloqueo de intrusos activado."
    
    conn = sqlite3.connect('db.sqlite')
    cursor = conn.cursor()
    cursor.execute("INSERT INTO logs (fecha, usuario, estado, ip) VALUES (?, ?, ?, ?)",
                   (ahora, "DEFENSE_UNIT", msg, "FIREWALL_ON"))
    conn.commit()
    conn.close()
    return jsonify({"mensaje": "Protocolo de Blindaje Ejecutado Correctamente."})

# --- ARRANQUE CORPORATIVO ---
if __name__ == '__main__':
    # Lanzamos en el puerto 5000 abierto para la red local
    app.run(host='0.0.0.0', port=5000, debug=True)
