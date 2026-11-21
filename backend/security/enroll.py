"""Tokens de unión efímeros (un solo uso) y firma de CSR para nodos nuevos."""
import argparse
import hashlib
import os
import re
import secrets
import sqlite3
import subprocess
import tempfile
import time
from contextlib import closing

DB = os.environ.get("CHRONO_ENROLL_DB", "data/enroll.db")


def _db(path=None):
    path = path or DB
    os.makedirs(os.path.dirname(path) or ".", mode=0o700, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS tokens ("
                "hash TEXT PRIMARY KEY, expires REAL NOT NULL, "
                "used INTEGER NOT NULL DEFAULT 0, label TEXT)")
    os.chmod(path, 0o600)
    return con


def _h(token):
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(ttl=600, label="", db=None):
    """Devuelve el token en claro (se muestra una vez). En disco solo queda su hash."""
    token = secrets.token_urlsafe(32)
    with closing(_db(db)) as con, con:
        con.execute("INSERT INTO tokens(hash, expires, label) VALUES (?,?,?)",
                    (_h(token), time.time() + ttl, label))
    return token


def consume_token(token, db=None):
    """True solo si el token existe, no ha expirado y no se ha usado. Atómico."""
    if not token:
        return False
    with closing(_db(db)) as con, con:
        cur = con.execute("UPDATE tokens SET used=1 WHERE hash=? AND used=0 AND expires>?",
                          (_h(token), time.time()))
        return cur.rowcount == 1


def sign_csr(csr_pem, node_id, ca_crt, ca_key, days=90):
    """Firma un CSR. El SAN lo fija el servidor a partir de node_id, no el cliente."""
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", node_id):
        raise ValueError("node_id inválido")
    with tempfile.TemporaryDirectory() as d:
        csr, crt, ext = (os.path.join(d, n) for n in ("n.csr", "n.crt", "n.ext"))
        with open(csr, "wb") as f:
            f.write(csr_pem)
        subprocess.run(["openssl", "req", "-in", csr, "-noout", "-verify"],
                       check=True, capture_output=True)
        with open(ext, "w") as f:
            f.write("basicConstraints=critical,CA:FALSE\n"
                    "keyUsage=critical,digitalSignature\n"
                    "extendedKeyUsage=clientAuth\n"
                    f"subjectAltName=DNS:{node_id}\n")
        subprocess.run(["openssl", "x509", "-req", "-in", csr, "-CA", ca_crt,
                        "-CAkey", ca_key, "-set_serial", "0x" + secrets.token_hex(16),
                        "-days", str(days), "-extfile", ext, "-out", crt],
                       check=True, capture_output=True)
        with open(crt, "rb") as f:
            return f.read()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    n = sub.add_parser("new-token")
    n.add_argument("--ttl", type=int, default=600)
    n.add_argument("--label", default="")
    a = ap.parse_args()
    print(create_token(a.ttl, a.label))
