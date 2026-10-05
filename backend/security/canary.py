import subprocess
import os
import json
import time
import base64
import sqlite3
from security.config_integrity import check_integrity, WATCHED_PATHS, _hash_file

CANARY_KEY_DIR = "canary_keys"
CANARY_KEY = f"{CANARY_KEY_DIR}/canary.key"
CANARY_PUB = f"{CANARY_KEY_DIR}/canary_pub.pem"
DB_PATH = "mesh_peers.db"

def ensure_canary_keypair():
    os.makedirs(CANARY_KEY_DIR, exist_ok=True)
    if not (os.path.exists(CANARY_KEY) and os.path.exists(CANARY_PUB)):
        subprocess.run(["openssl", "genrsa", "-out", CANARY_KEY, "2048"],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["openssl", "rsa", "-in", CANARY_KEY, "-pubout", "-out", CANARY_PUB],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def init_canary_table():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS canary_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            published_at REAL,
            statement TEXT,
            signature_b64 TEXT
        )
    """)
    conn.commit()
    conn.close()

def publish_canary(node_id):
    ensure_canary_keypair()
    init_canary_table()

    config_hashes = {p: _hash_file(p) for p in WATCHED_PATHS}
    statement = {
        "node_id": node_id,
        "timestamp": time.time(),
        "declaration": "Este nodo esta operando bajo control legitimo de su operador. No ha sido comprometido, intervenido fisicamente, ni modificado sin autorizacion al momento de esta firma.",
        "code_integrity": config_hashes,
    }
    statement_json = json.dumps(statement, sort_keys=True)

    tmp_path = "canary_keys/.tmp_statement.json"
    with open(tmp_path, "w") as f:
        f.write(statement_json)

    sig_path = "canary_keys/.tmp_statement.sig"
    subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", CANARY_KEY, "-out", sig_path, tmp_path],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    with open(sig_path, "rb") as f:
        signature_b64 = base64.b64encode(f.read()).decode()

    os.remove(tmp_path)
    os.remove(sig_path)

    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO canary_log (published_at, statement, signature_b64) VALUES (?, ?, ?)",
        (statement["timestamp"], statement_json, signature_b64)
    )
    conn.commit()
    conn.close()

    return statement, signature_b64

def get_latest_canary():
    init_canary_table()
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT published_at, statement, signature_b64 FROM canary_log ORDER BY published_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if not row:
        return None
    pubkey = ""
    if os.path.exists(CANARY_PUB):
        with open(CANARY_PUB) as f:
            pubkey = f.read()
    return {
        "published_at": row[0],
        "statement": json.loads(row[1]),
        "signature_b64": row[2],
        "public_key_pem": pubkey
    }
