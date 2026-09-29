import hashlib
import os
import json

BASELINE_PATH = "security/config_baseline.json"
WATCHED_PATHS = [
    "../router-config/chronoshield.conf",
    "../router-config/nginx-mtls.conf",
]

def _hash_file(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            h.update(block)
    return h.hexdigest()

def establish_baseline():
    baseline = {p: _hash_file(p) for p in WATCHED_PATHS}
    with open(BASELINE_PATH, "w") as f:
        json.dump(baseline, f, indent=2)
    return baseline

def check_integrity():
    if not os.path.exists(BASELINE_PATH):
        establish_baseline()
        return []
    with open(BASELINE_PATH) as f:
        baseline = json.load(f)
    changes = []
    for path, old_hash in baseline.items():
        new_hash = _hash_file(path)
        if new_hash != old_hash:
            changes.append({"path": path, "expected": old_hash, "found": new_hash})
    return changes
