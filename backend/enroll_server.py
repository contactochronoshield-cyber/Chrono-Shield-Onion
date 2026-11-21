"""Listener de enrolamiento (puerto 5444): TLS sin cert de cliente.
Solo expone /ca.crt, /enroll (token de un solo uso) y /canary (público, solo lectura)."""
import logging
import os
import re
import ssl
import time
from collections import defaultdict, deque

from flask import Flask, Response, jsonify, request

try:
    from backend.security import enroll
except ImportError:
    from security import enroll

logger = logging.getLogger("ChronoEnroll")
MAX_CSR = 8192
_hits = defaultdict(lambda: deque(maxlen=20))


def _limited(ip, limit=10, window=60):
    now = time.time()
    q = _hits[ip]
    while q and now - q[0] > window:
        q.popleft()
    if len(q) >= limit:
        return True
    q.append(now)
    return False


def create_app(certs_dir="certs", canary_getter=None):
    app = Flask("chrono-enroll")
    ca_crt = os.path.join(certs_dir, "ca.crt")
    ca_key = os.environ.get("CHRONO_CA_KEY", os.path.join(certs_dir, "ca.key"))

    @app.route("/ca.crt", methods=["GET"])
    def ca():
        with open(ca_crt, "rb") as f:
            return Response(f.read(), mimetype="application/x-pem-file")

    @app.route("/canary", methods=["GET"])
    def public_canary():
        data = canary_getter() if canary_getter else None
        if not data:
            return jsonify({"error": "NO_CANARY_PUBLISHED_YET"}), 404
        resp = jsonify(data)
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Cache-Control"] = "no-store"
        return resp, 200

    @app.route("/enroll", methods=["POST"])
    def do_enroll():
        if _limited(request.remote_addr):
            return jsonify({"error": "RATE_LIMITED"}), 429
        data = request.get_json(silent=True) or {}
        token = data.get("token")
        node_id = data.get("node_id")
        csr = data.get("csr")
        if not all(isinstance(x, str) for x in (token, node_id, csr)):
            return jsonify({"error": "BAD_REQUEST"}), 400
        if len(csr) > MAX_CSR or not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", node_id):
            return jsonify({"error": "BAD_REQUEST"}), 400
        if not enroll.consume_token(token):
            logger.warning("Enrolamiento rechazado (token inválido/usado/expirado) desde %s",
                           request.remote_addr)
            return jsonify({"error": "INVALID_TOKEN"}), 403
        try:
            crt = enroll.sign_csr(csr.encode(), node_id, ca_crt, ca_key)
        except Exception as e:
            logger.error("Fallo firmando CSR de %s: %s", node_id, e)
            return jsonify({"error": "SIGN_FAILED"}), 500
        logger.warning("Nodo enrolado: %s desde %s", node_id, request.remote_addr)
        return jsonify({"certificate": crt.decode()}), 200

    return app


def run_enroll_server(certs_dir="certs", port=5444, canary_getter=None):
    app = create_app(certs_dir, canary_getter)
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(os.path.join(certs_dir, "server.crt"),
                        os.path.join(certs_dir, "server.key"))
    ctx.verify_mode = ssl.CERT_NONE
    app.run(host="0.0.0.0", port=port, ssl_context=ctx, debug=False)
