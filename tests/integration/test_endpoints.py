from dotenv import load_dotenv
import os
import requests
import pytest

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
    assert "Use /ip/<ip>" in response.text

def test_ip_endpoint_success():
    ip = "8.8.8.8"
    response = requests.get(f"{BASE_URL}/ip/{ip}")
    assert response.status_code == 200
    data = response.json()
    assert data["ip"] == ip
    assert "country" in data
    assert "city" in data
