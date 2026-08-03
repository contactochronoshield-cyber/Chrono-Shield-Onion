import pytest
import sys
import os
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

TEST_PASSWORD = "test-pass-ci-only-123"
os.environ["CHRONO_JWT_SECRET"] = "test-secret-not-for-production-ci-only"
os.environ["CHRONO_ADMIN_USER"] = "testadmin"
os.environ["CHRONO_ADMIN_PASS_HASH"] = generate_password_hash(TEST_PASSWORD)

from api import app, JWT_SECRET
import jwt

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "chrono-shield-core"

def test_metrics_endpoint(client):
    response = client.get('/metrics')
    assert response.status_code == 200
    assert b"chrono_cpu_percent" in response.data
    assert b"chrono_memory_percent" in response.data

def test_login_wrong_credentials(client):
    response = client.post('/api/v1/auth/login', json={"username": "testadmin", "password": "wrong"})
    assert response.status_code == 401

def test_login_correct_credentials(client):
    response = client.post('/api/v1/auth/login', json={"username": "testadmin", "password": TEST_PASSWORD})
    assert response.status_code == 200
    data = response.get_json()
    assert "access_token" in data

def test_telemetry_unauthorized(client):
    response = client.get('/api/v1/telemetry')
    assert response.status_code == 401

def test_telemetry_authorized(client):
    token = jwt.encode({"sub": "test-suite-agent", "exp": 9999999999}, JWT_SECRET, algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get('/api/v1/telemetry', headers=headers)
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "SECURE_TELEMETRY_STREAM"
    assert "metrics" in data
    assert "security_audit" in data
