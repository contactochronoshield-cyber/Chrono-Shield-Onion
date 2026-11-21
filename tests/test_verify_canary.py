import base64, json, os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.verify_canary import verify_data


def _firmado(tmp_path, statement):
    key, pub = str(tmp_path / "k.pem"), str(tmp_path / "p.pem")
    subprocess.run(["openssl", "genrsa", "-out", key, "2048"], check=True, capture_output=True)
    subprocess.run(["openssl", "rsa", "-in", key, "-pubout", "-out", pub], check=True, capture_output=True)
    msg = str(tmp_path / "m.json")
    open(msg, "w").write(json.dumps(statement, sort_keys=True))
    sig = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key, msg],
                         check=True, capture_output=True).stdout
    return {"statement": statement, "signature_b64": base64.b64encode(sig).decode(),
            "public_key_pem": open(pub).read()}


def test_firma_valida_y_pin(tmp_path):
    d = _firmado(tmp_path, {"declaration": "ok", "node_id": "n1"})
    ok, pinned, fp = verify_data(d)
    assert ok and pinned is None
    assert verify_data(d, pin=fp)[1] is True
    assert verify_data(d, pin="00" * 32)[1] is False


def test_statement_alterado(tmp_path):
    d = _firmado(tmp_path, {"declaration": "ok", "node_id": "n1"})
    d["statement"]["declaration"] = "comprometido"
    assert verify_data(d)[0] is False
