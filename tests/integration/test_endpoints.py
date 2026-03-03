import os

import requests
from dotenv import load_dotenv

load_dotenv()

# Use BASE_URL from .env if set, otherwise construct from FLASK_PORT
BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    BASE_URL = f"http://127.0.0.1:{FLASK_PORT}"


def test_health():
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json() == {"status": "UP"}


def test_index():
    response = requests.get(f"{BASE_URL}/")
    assert response.status_code == 200

    data = response.json()
    assert "service" in data
    assert "endpoints" in data
    assert "GET /ip/<ip>" in data["endpoints"]


def test_ip_endpoint_success():
    ip = "8.8.8.8"
    response = requests.get(f"{BASE_URL}/ip/{ip}")
    assert response.status_code == 200
    data = response.json()
    assert data["ip"] == ip
    assert "country" in data
    assert "city" in data


def test_metrics():
    response = requests.get(f"{BASE_URL}/metrics")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/plain")
    assert "# HELP" in response.text
    assert "# TYPE" in response.text


def test_store_endpoint_success():
    response = requests.post(f"{BASE_URL}/store")

    assert response.status_code == 200
    assert response.json()["status"] == "stored"


def test_metrics_after_request():
    ip = "1.1.1.1"

    requests.get(f"{BASE_URL}/ip/{ip}")
    metrics = requests.get(f"{BASE_URL}/metrics")

    assert "ip_checker_requests_total" in metrics.text
