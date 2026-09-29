#!/bin/bash
# Rotacion de CA: invalida certificados existentes, genera nueva CA.
# Uso: manual, o programable via cron. Los peers deben re-registrarse (mesh_client.py) tras rotar.
cd ~/Chrono-Shield-Onion/backend/certs
TS=$(date +%s)
mkdir -p ../certs_archive
mv ca.crt ca.key server.crt server.key ../certs_archive/ 2>/dev/null
echo "[+] CA antigua archivada en certs_archive/ (timestamp $TS)"
openssl req -x509 -new -nodes -days 365 -newkey rsa:2048 -keyout ca.key -out ca.crt -subj "/CN=ChronoShieldRootCA" -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign"
openssl req -new -nodes -newkey rsa:2048 -keyout server.key -out server.csr -subj "/CN=localhost"
echo "subjectAltName=DNS:localhost,IP:127.0.0.1" > server_ext.cnf
openssl x509 -req -days 365 -in server.csr -CA ca.crt -CAkey ca.key -set_serial 01 -out server.crt -extfile server_ext.cnf
echo "[+] Nueva CA y certificado de servidor generados. Los peers deben re-registrarse."
