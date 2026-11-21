import os, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.security import enroll
from backend.security.crypto import ensure_tls_certificates


def test_token_un_solo_uso(tmp_path):
    db = str(tmp_path / "e.db")
    t = enroll.create_token(600, db=db)
    assert enroll.consume_token(t, db=db) is True
    assert enroll.consume_token(t, db=db) is False


def test_token_invalido_o_vacio(tmp_path):
    db = str(tmp_path / "e.db")
    assert enroll.consume_token("falso", db=db) is False
    assert enroll.consume_token("", db=db) is False


def test_token_expirado(tmp_path):
    db = str(tmp_path / "e.db")
    t = enroll.create_token(-1, db=db)
    assert enroll.consume_token(t, db=db) is False


def test_firma_csr_y_validacion(tmp_path):
    certs = str(tmp_path / "certs")
    ensure_tls_certificates(certs)
    key, csr = str(tmp_path / "n.key"), str(tmp_path / "n.csr")
    subprocess.run(["openssl", "req", "-new", "-nodes", "-newkey", "rsa:2048",
                    "-keyout", key, "-out", csr, "-subj", "/CN=nodo-x"],
                   check=True, capture_output=True)
    crt_pem = enroll.sign_csr(open(csr, "rb").read(), "nodo-x",
                              f"{certs}/ca.crt", f"{certs}/ca.key")
    crt = str(tmp_path / "n.crt")
    open(crt, "wb").write(crt_pem)
    r = subprocess.run(["openssl", "verify", "-CAfile", f"{certs}/ca.crt", crt],
                       capture_output=True, text=True)
    assert "OK" in r.stdout


def test_node_id_malicioso(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        enroll.sign_csr(b"x", "a;b", "x", "y")
