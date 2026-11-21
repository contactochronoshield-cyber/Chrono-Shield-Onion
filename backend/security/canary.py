import os
import json
import time
import base64
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from security.config_integrity import (
    check_integrity, WATCHED_PATHS, _hash_file
)

ROOT = Path(__file__).resolve().parents[2]
_DATA = os.environ.get("CHRONO_DATA_DIR")

DATA_DIR = Path(_DATA).expanduser().resolve() if _DATA else ROOT
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Conservar las claves existentes si no se ha configurado
# previamente un directorio de datos externo.
LEGACY_KEY_DIR = ROOT / "backend" / "canary_keys"
CANARY_KEY_DIR = (
    DATA_DIR / "canary_keys"
    if _DATA else LEGACY_KEY_DIR
)
CANARY_KEY = CANARY_KEY_DIR / "canary.key"
CANARY_PUB = CANARY_KEY_DIR / "canary_pub.pem"

DB_PATH = (
    Path(_os.path.join(_DATA, "mesh_peers.db")).resolve()
    if _DATA else Path("mesh_peers.db").resolve()
)


def ensure_canary_keypair():
    CANARY_KEY_DIR.mkdir(parents=True, exist_ok=True)

    if CANARY_KEY.exists() and not CANARY_PUB.exists():
        # Recuperar la pública desde la privada existente.
        subprocess.run(
            ["openssl", "rsa", "-in", str(CANARY_KEY),
             "-pubout", "-out", str(CANARY_PUB)],
            check=True, capture_output=True
        )

    elif CANARY_PUB.exists() and not CANARY_KEY.exists():
        raise RuntimeError(
            "Existe la clave pública, pero falta la privada. "
            "No se generará otra identidad automáticamente."
        )

    elif not CANARY_KEY.exists() and not CANARY_PUB.exists():
        subprocess.run(
            ["openssl", "genrsa", "-out", str(CANARY_KEY), "2048"],
            check=True, capture_output=True
        )
        subprocess.run(
            ["openssl", "rsa", "-in", str(CANARY_KEY),
             "-pubout", "-out", str(CANARY_PUB)],
            check=True, capture_output=True
        )

    os.chmod(CANARY_KEY, 0o600)
    os.chmod(CANARY_PUB, 0o644)

    # Comprobar que la pública corresponde a la privada.
    derived = subprocess.run(
        ["openssl", "rsa", "-in", str(CANARY_KEY), "-pubout"],
        check=True, capture_output=True
    ).stdout.strip()

    actual = CANARY_PUB.read_bytes().strip()

    if derived != actual:
        raise RuntimeError(
            "La clave pública no corresponde a la privada."
        )


def init_canary_table():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS canary_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                published_at REAL,
                statement TEXT,
                signature_b64 TEXT
            )
        """)


def publish_canary(node_id):
    ensure_canary_keypair()
    init_canary_table()

    config_hashes = {
        str(p): _hash_file(p) for p in WATCHED_PATHS
    }

    statement = {
        "node_id": node_id,
        "timestamp": time.time(),
        "declaration": (
            "El nodo publica una declaración firmada de su estado "
            "de integridad supervisado. La firma no certifica por "
            "sí sola la ausencia de compromiso físico o lógico."
        ),
        "code_integrity": config_hashes,
    }

    statement_json = json.dumps(
        statement, sort_keys=True, separators=(",", ":")
    )

    # Temporales dentro del directorio de claves, no en cwd.
    with tempfile.TemporaryDirectory(dir=CANARY_KEY_DIR) as tmp:
        msg = Path(tmp) / "statement.json"
        sig = Path(tmp) / "statement.sig"

        msg.write_text(statement_json, encoding="utf-8")

        subprocess.run(
            ["openssl", "dgst", "-sha256", "-sign",
             str(CANARY_KEY), "-out", str(sig), str(msg)],
            check=True, capture_output=True
        )

        signature_b64 = base64.b64encode(
            sig.read_bytes()
        ).decode("ascii")

    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO canary_log "
            "(published_at, statement, signature_b64) "
            "VALUES (?, ?, ?)",
            (statement["timestamp"], statement_json, signature_b64)
        )

    return statement, signature_b64


def get_latest_canary():
    init_canary_table()

    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT published_at, statement, signature_b64 "
            "FROM canary_log ORDER BY published_at DESC LIMIT 1"
        ).fetchone()

    if not row:
        return None

    if not CANARY_PUB.exists():
        raise RuntimeError("No existe la clave pública Canary.")

    pubkey = CANARY_PUB.read_text(encoding="utf-8")

    return {
        "published_at": row[0],
        "statement_raw": row[1],
        "statement": json.loads(row[1]),
        "signature_b64": row[2],
        "public_key_pem": pubkey,
    }
