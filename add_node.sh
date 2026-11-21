#!/bin/bash
# Uso: ./add_node.sh [segundos_de_vigencia] [etiqueta]
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT/backend"
FP=$(openssl x509 -in certs/ca.crt -noout -fingerprint -sha256 | cut -d= -f2)
TOKEN=$(PYTHONPATH="$ROOT" python -m backend.security.enroll new-token --ttl "${1:-600}" --label "${2:-}")
echo "Token de un solo uso (vence en ${1:-600}s). En el nodo nuevo ejecuta:"
echo
echo "export CHRONO_MAIN_NODE=<IP_o_dominio_de_este_nodo>"
echo "export CHRONO_NODE_ID=<nombre-del-nodo>"
echo "export CHRONO_ENROLL_TOKEN=$TOKEN"
echo "export CHRONO_CA_SHA256=$FP"
echo "python backend/mesh_client.py"
