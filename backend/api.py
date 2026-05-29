from flask import Flask, jsonify
import random

app = Flask(__name__)

@app.route("/api/metrics", methods=["GET"])
def get_metrics():
    return jsonify({
        "status": "SECURE",
        "encryption": "AES-256-GCM",
        "cpu": f"{random.randint(12, 26)}%",
        "ram": f"{random.randint(48, 64)}%",
        "active_nodes": random.randint(9, 16),
        "tunnel_status": "TUNNEL_ACTIVE"
    })

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
