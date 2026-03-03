"""Unit tests for IP Checker API."""

from src.app import app


def test_health_endpoint():
    """Health endpoint should return service status."""
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "UP"}


def test_index_endpoint():
    """Root endpoint should return usage instructions."""
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    data = response.json
    assert "service" in data
    assert "endpoints" in data
    assert "GET /ip/<ip>" in data["endpoints"]


def test_ip_endpoint_success(mocker):
    """IP endpoint should return parsed IP data from external API."""
    mock_response = {
        "country": "United States",
        "countryCode": "US",
        "city": "Ashburn",
        "isp": "Google LLC",
    }

    mocker.patch("requests.get", return_value=mocker.Mock(json=lambda: mock_response))

    # Mock Redis cache
    mock_cache = mocker.patch("src.app.cache")
    mock_cache.get.return_value = None
    mock_cache.set.return_value = True

    client = app.test_client()
    response = client.get("/ip/8.8.8.8")

    assert response.status_code == 200
    assert response.json == {
        "ip": "8.8.8.8",
        "country": "United States",
        "countryCode": "US",
        "city": "Ashburn",
        "isp": "Google LLC",
    }


def test_store_endpoint(mocker):
    """Store endpoint should trigger cache save and return status."""
    mocker.patch("src.app.save_cache_once")  # Nu face backup real

    client = app.test_client()
    response = client.post("/store")

    assert response.status_code == 200
    assert response.json == {"status": "stored"}


def test_store_endpoint_error(mocker):
    """If saving cache fails, endpoint returns error."""
    mocker.patch("src.app.save_cache_once", side_effect=Exception("fail"))

    client = app.test_client()
    response = client.post("/store")

    assert response.status_code == 500
    assert "error" in response.json


def test_metrics_endpoint():
    """Metrics endpoint should return Prometheus metrics."""
    client = app.test_client()
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.content_type.startswith("text/plain")
    assert b"# HELP" in response.data
    assert b"# TYPE" in response.data
