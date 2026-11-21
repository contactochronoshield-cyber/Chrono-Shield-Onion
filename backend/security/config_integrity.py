import os
import json
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_DATA = os.environ.get("CHRONO_DATA_DIR")

DATA_DIR = Path(_DATA).expanduser().resolve() if _DATA else (
    ROOT / "backend" / "security"
)
DATA_DIR.mkdir(parents=True, exist_ok=True)

BASELINE_PATH = DATA_DIR / "config_baseline.json"

WATCHED_PATHS = [
    ROOT / "router-config" / "chronoshield.conf",
    ROOT / "router-config" / "nginx-mtls.conf",
]


def _hash_file(path):
    path = Path(path)
    if not path.is_file():
        return None

    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            h.update(block)
    return h.hexdigest()


def establish_baseline():
    """
    Actualización administrativa explícita.
    No debe llamarse automáticamente al detectar cambios.
    """
    baseline = {
        str(path): _hash_file(path)
        for path in WATCHED_PATHS
    }

    temp_path = BASELINE_PATH.with_suffix(".tmp")

    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(baseline, f, indent=2)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_path, BASELINE_PATH)
    os.chmod(BASELINE_PATH, 0o600)

    return baseline


def check_integrity():
    """
    Solo detecta. Nunca crea ni actualiza automáticamente
    una línea base ausente o modificada.
    """
    if not BASELINE_PATH.exists():
        return [{
            "path": str(BASELINE_PATH),
            "expected": "BASELINE_EXISTS",
            "found": "MISSING",
        }]

    try:
        with BASELINE_PATH.open(encoding="utf-8") as f:
            baseline = json.load(f)
    except (OSError, ValueError):
        return [{
            "path": str(BASELINE_PATH),
            "expected": "VALID_BASELINE",
            "found": "UNREADABLE_OR_INVALID",
        }]

    changes = []

    for path, old_hash in baseline.items():
        new_hash = _hash_file(path)
        if new_hash != old_hash:
            changes.append({
                "path": path,
                "expected": old_hash,
                "found": new_hash,
            })

    return changes
