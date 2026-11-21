#!/bin/bash
# Rota la CA y el certificado del servidor. Los peers deben re-enrolarse.
set -e
cd "$(dirname "$0")"
if [ -z "$CHRONO_SKIP_RUNNING_CHECK" ] && pgrep -f "supervisor.py|mesh_server.py" >/dev/null; then
  echo "ERROR: detén el supervisor y el mesh_server antes de rotar." >&2
  exit 1
fi
if [ -d certs ]; then
  OLD="certs.old.$(date +%Y%m%d-%H%M%S)"
  mv certs "$OLD"
  chmod 700 "$OLD"
  echo "[+] Certificados anteriores archivados en $OLD"
fi
python -c "from backend.security.crypto import ensure_tls_certificates as e; e('certs')"
echo "[+] Nueva CA. Huella SHA-256 (entrégala a los peers):"
openssl x509 -in certs/ca.crt -noout -fingerprint -sha256 | cut -d= -f2
echo "[!] Los peers deben borrar peer_certs/ y re-enrolarse con un token nuevo."
