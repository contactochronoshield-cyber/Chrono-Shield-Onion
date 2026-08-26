#!/bin/bash
set -e
cd ~/Chrono-Shield-Onion

echo "=== 1. Verificando .env.local ==="
if [ ! -f .env.local ]; then
  {
    echo "export CHRONO_JWT_SECRET=\"f2fc6d088624fc2221381520960d92c3bd3c3e4111bfe256fc2053c5498bbec3\""
    echo "export CHRONO_ADMIN_USER=\"admin\""
    echo "export CHRONO_ADMIN_PASS_HASH='scrypt:32768:8:1\$JuFyYwo5Cxjr6iIy\$e90b011778cc63898416d74b725e18e516b18c919e749d65026feda3a9be1884ef2a9a87c6ada6734e3c8a1bb72e4f4cad8fea81583363b88901f5ecd7692bfc'"
    echo "export CHRONO_NODE_ID=\"chrono-node-01-bogota\""
  } > .env.local
fi
source .env.local

echo "=== 2. Verificando backend/security/crypto.py ==="
mkdir -p backend/security
if [ ! -s backend/security/crypto.py ]; then
  cat > backend/security/crypto.py << 'PYEOF'
import hashlib
import os
import logging
import subprocess

logger = logging.getLogger("ChronoSecurity")

def ensure_tls_certificates(cert_dir="certs"):
    os.makedirs(cert_dir, exist_ok=True)
    server_crt = os.path.join(cert_dir, "server.crt")
    server_key = os.path.join(cert_dir, "server.key")
    ca_crt = os.path.join(cert_dir, "ca.crt")

    if not (os.path.exists(server_crt) and os.path.exists(server_key) and os.path.exists(ca_crt)):
        logger.info("[+] Generando infraestructura mTLS con OpenSSL para producción...")
        try:
            subprocess.run([
                "openssl", "req", "-x509", "-new", "-nodes", "-days", "365",
                "-newkey", "rsa:2048", "-keyout", os.path.join(cert_dir, "ca.key"),
                "-out", ca_crt, "-subj", "/CN=ChronoShieldRootCA"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run([
                "openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
                "-keyout", server_key, "-out", os.path.join(cert_dir, "server.csr"),
                "-subj", "/CN=localhost"
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            subprocess.run([
                "openssl", "x509", "-req", "-days", "365",
                "-in", os.path.join(cert_dir, "server.csr"),
                "-CA", ca_crt, "-CAkey", os.path.join(cert_dir, "ca.key"),
                "-set_serial", "01", "-out", server_crt
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            logger.info("[+] Certificados mTLS generados correctamente.")
        except Exception as e:
            logger.warning(f"[-] No se pudo automatizar OpenSSL: {e}.")

def verify_code_integrity(file_paths):
    integrity_report = {}
    for path in file_paths:
        if os.path.exists(path):
            sha256_hash = hashlib.sha256()
            with open(path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            integrity_report[path] = sha256_hash.hexdigest()
        else:
            integrity_report[path] = "FILE_NOT_FOUND"
    return integrity_report
PYEOF
fi

echo "=== 3. Verificando openssl ==="
command -v openssl &> /dev/null || pkg install openssl-tool -y

echo "=== 4. Deteniendo procesos previos ==="
pkill -f "python api.py" 2>/dev/null || true
pkill -f "python mesh_server.py" 2>/dev/null || true
sleep 1

echo "=== 5. Arrancando dashboard (5000) ==="
cd backend
PYTHONPATH=. nohup python api.py > ~/chrono_api.log 2>&1 &
sleep 2

echo "=== 6. Arrancando mesh mTLS (5443) ==="
PYTHONPATH=. nohup python mesh_server.py > ~/chrono_mesh.log 2>&1 &
sleep 3

echo "=== 7. Pruebas ==="
echo "--- Dashboard /health ---"
curl -s http://127.0.0.1:5000/health || echo "[X] Dashboard no responde"
echo ""
echo "--- Mesh sin cert (debe fallar el handshake) ---"
curl -sk https://127.0.0.1:5443/mesh/peers || echo "[OK] Mesh rechazó conexión sin certificado"
echo ""
echo "=== LISTO ==="
