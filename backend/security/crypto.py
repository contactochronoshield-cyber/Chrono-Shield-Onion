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
        try:
            subprocess.run(["openssl", "req", "-x509", "-new", "-nodes", "-days", "365",
                "-newkey", "rsa:2048", "-keyout", os.path.join(cert_dir, "ca.key"),
                "-out", ca_crt, "-subj", "/CN=ChronoShieldRootCA"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
                "-keyout", server_key, "-out", os.path.join(cert_dir, "server.csr"),
                "-subj", "/CN=localhost"],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["openssl", "x509", "-req", "-days", "365",
                "-in", os.path.join(cert_dir, "server.csr"),
                "-CA", ca_crt, "-CAkey", os.path.join(cert_dir, "ca.key"),
                "-set_serial", "01", "-out", server_crt],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.warning(f"No se pudo automatizar OpenSSL: {e}")

def verify_code_integrity(file_paths):
    report = {}
    for path in file_paths:
        if os.path.exists(path):
            h = hashlib.sha256()
            with open(path, "rb") as f:
                for block in iter(lambda: f.read(4096), b""):
                    h.update(block)
            report[path] = h.hexdigest()
        else:
            report[path] = "FILE_NOT_FOUND"
    return report
