"""Identidad de un peer a partir de su certificado de cliente (SAN DNS)."""
import os


def cert_identity(peercert):
    if not peercert:
        return None
    for kind, val in peercert.get("subjectAltName", ()):
        if kind == "DNS" and val != "localhost":
            return val
    return None


def resolve_peer_identity(peercert, claimed):
    """Devuelve (node_id, error). Error: 'mismatch' o 'no_identity'."""
    ident = cert_identity(peercert)
    if ident:
        if claimed and claimed != ident:
            return None, "mismatch"
        return ident, None
    if os.environ.get("CHRONO_ALLOW_LEGACY_IDENTITY") == "1":
        return claimed or "unknown", None
    return None, "no_identity"


def get_peercert(environ):
    """Certificado del cliente desde el socket TLS de Werkzeug (formato dict con SAN)."""
    sock = environ.get("werkzeug.socket")
    if sock is not None:
        try:
            cert = sock.getpeercert()
            if cert:
                return cert
        except Exception:
            pass
    return environ.get("peercert")
