import os, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import pytest
from backend.security import enroll
from backend.security.crypto import ensure_tls_certificates
from backend import enroll_server


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(enroll, "DB", str(tmp_path / "e.db"))
    certs = str(tmp_path / "certs")
    ensure_tls_certificates(certs)
    enroll_server._hits.clear()
    app = enroll_server.create_app(certs, canary_getter=lambda: {"ok": True})
    return app.test_client(), certs, tmp_path


def _csr(tmp_path, cn):
    key, csr = str(tmp_path / "k.key"), str(tmp_path / "k.csr")
    subprocess.run(["openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
                    "-keyout", key, "-out", csr, "-subj", f"/CN={cn}"],
                   check=True, capture_output=True)
    return open(csr).read()


def test_enrolamiento_ok_y_un_solo_uso(env):
    c, certs, tmp = env
    t = enroll.create_token(600)
    body = {"token": t, "node_id": "nodo-a", "csr": _csr(tmp, "nodo-a")}
    r = c.post("/enroll", json=body)
    assert r.status_code == 200
    crt = str(tmp / "n.crt")
    open(crt, "w").write(r.get_json()["certificate"])
    v = subprocess.run(["openssl", "verify", "-CAfile", f"{certs}/ca.crt", crt],
                       capture_output=True, text=True)
    assert "OK" in v.stdout
    assert c.post("/enroll", json=body).status_code == 403  # token ya usado


def test_token_falso(env):
    c, _, tmp = env
    r = c.post("/enroll", json={"token": "x", "node_id": "n", "csr": _csr(tmp, "n")})
    assert r.status_code == 403


def test_node_id_malo_no_quema_token(env):
    c, _, tmp = env
    t = enroll.create_token(600)
    r = c.post("/enroll", json={"token": t, "node_id": "a;rm", "csr": "x"})
    assert r.status_code == 400
    assert enroll.consume_token(t) is True


def test_ca_y_canary_publicos(env):
    c, _, _ = env
    assert b"BEGIN CERTIFICATE" in c.get("/ca.crt").data
    assert c.get("/canary").get_json() == {"ok": True}
