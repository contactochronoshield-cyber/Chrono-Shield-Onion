import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from backend.security.identity import resolve_peer_identity as r

CERT = {"subjectAltName": (("DNS", "nodo-a"),)}


def test_identidad_ok():
    assert r(CERT, "nodo-a") == ("nodo-a", None)
    assert r(CERT, None) == ("nodo-a", None)


def test_suplantacion():
    assert r(CERT, "nodo-b") == (None, "mismatch")


def test_sin_san_rechazado(monkeypatch):
    monkeypatch.delenv("CHRONO_ALLOW_LEGACY_IDENTITY", raising=False)
    assert r({}, "nodo-a") == (None, "no_identity")
    assert r(None, "nodo-a") == (None, "no_identity")


def test_modo_legacy(monkeypatch):
    monkeypatch.setenv("CHRONO_ALLOW_LEGACY_IDENTITY", "1")
    assert r({}, "nodo-a") == ("nodo-a", None)


def test_localhost_no_cuenta():
    assert r({"subjectAltName": (("DNS", "localhost"),)}, "x") == (None, "no_identity")


def test_get_peercert_desde_socket():
    from backend.security.identity import get_peercert

    class S:
        def getpeercert(self):
            return {"subjectAltName": (("DNS", "x"),)}

    assert get_peercert({"werkzeug.socket": S()})["subjectAltName"][0][1] == "x"
    assert get_peercert({}) is None
