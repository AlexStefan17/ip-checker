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
    assert "Use /ip/<ip>" in response.data.decode()


def test_ip_endpoint_success(mocker):
    """IP endpoint should return parsed IP data from external API."""
    mock_response = {
        "country": "United States",
        "countryCode": "US",
        "city": "Ashburn",
        "isp": "Google LLC"
    }

    mocker.patch(
        "requests.get",
        return_value=mocker.Mock(json=lambda: mock_response)
    )

    client = app.test_client()
    response = client.get("/ip/8.8.8.8")

    assert response.status_code == 200
    assert response.json == {
        "ip": "8.8.8.8",
        "country": "United States",
        "countryCode": "US",
        "city": "Ashburn",
        "isp": "Google LLC"
    }
