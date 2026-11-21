import hashlib
import logging
import os
import secrets
import subprocess
import tempfile

logger = logging.getLogger("ChronoSecurity")


def _run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _san():
    """SAN desde CHRONO_SAN (ej: 'DNS:nodo.example.com,IP:10.0.0.5')."""
    extra = os.environ.get("CHRONO_SAN", "")
    base = ["DNS:localhost", "IP:127.0.0.1"]
    return ",".join(base + [x.strip() for x in extra.split(",") if x.strip()])


def ensure_tls_certificates(cert_dir="certs"):
    os.makedirs(cert_dir, mode=0o700, exist_ok=True)
    os.chmod(cert_dir, 0o700)
    p = lambda n: os.path.join(cert_dir, n)

    if all(os.path.exists(p(f)) for f in ("server.crt", "server.key", "ca.crt")):
        return

    logger.info("[+] Generando CA y certificado de servidor (mTLS)...")
    try:
        # CA: marcada como CA, solo puede firmar certificados
        _run(["openssl", "req", "-x509", "-new", "-nodes", "-days", "3650",
              "-newkey", "rsa:3072", "-keyout", p("ca.key"), "-out", p("ca.crt"),
              "-subj", "/CN=ChronoShieldRootCA",
              "-addext", "basicConstraints=critical,CA:TRUE,pathlen:0",
              "-addext", "keyUsage=critical,keyCertSign,cRLSign"])

        _run(["openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
              "-keyout", p("server.key"), "-out", p("server.csr"),
              "-subj", "/CN=localhost"])

        ext = (
            "basicConstraints=critical,CA:FALSE\n"
            "keyUsage=critical,digitalSignature,keyEncipherment\n"
            "extendedKeyUsage=serverAuth,clientAuth\n"
            f"subjectAltName={_san()}\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".ext", delete=False) as f:
            f.write(ext)
            extfile = f.name
        try:
            _run(["openssl", "x509", "-req", "-days", "365", "-in", p("server.csr"),
                  "-CA", p("ca.crt"), "-CAkey", p("ca.key"),
                  "-set_serial", "0x" + secrets.token_hex(16),
                  "-extfile", extfile, "-out", p("server.crt")])
        finally:
            os.remove(extfile)

        for name in ("ca.key", "server.key"):
            os.chmod(p(name), 0o600)
        logger.info("[+] Certificados mTLS generados correctamente.")
    except Exception as e:
        logger.error("[-] Error generando certificados: %s", e)
        raise


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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
