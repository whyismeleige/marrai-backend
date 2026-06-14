from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

from main import app
from tests.fixtures import fake_result, fake_empty_result, fake_blocked_result

client = TestClient(app)


def test_successful_audit():
    with patch(
        "app.api.routes.audit.orchestrate", AsyncMock(return_value=fake_result)
    ) as mock_orchestrate:
        response = client.post("/api/v1/audit", json={"url": "https://example.com"})

        assert response.status_code == 200

        data = response.json()

        assert data["url"] == "https://example.com"
        assert data["overall_score"] == 80
        assert len(data["pages"]) == 1

        mock_orchestrate.assert_awaited_once()


def test_malformed_seed_url():
    response = client.post("/api/v1/audit", json={"url": "abcd"})
    assert response.status_code == 422


def test_empty_audit():
    with patch(
        "app.api.routes.audit.orchestrate", AsyncMock(return_value=fake_empty_result)
    ) as mock_orchestrate:
        response = client.post("/api/v1/audit", json={"url": "https://example.com"})

        assert response.status_code == 503
        assert (
            response.json()["detail"]
            == "The target website could not be reached. Please verify the URL and try again."
        )


def test_server_errors():
    with patch(
        "app.api.routes.audit.orchestrate",
        AsyncMock(side_effect=Exception("DNS failure")),
    ):
        response = client.post("/api/v1/audit", json={"url": "https://example.com"})

        assert response.status_code == 500
        assert (
            response.json()["detail"]
            == "An unexpected error occured during the audit. Please try again."
        )


def test_blocked_audit():
    with patch(
        "app.api.routes.audit.orchestrate", AsyncMock(return_value=fake_blocked_result)
    ) as mock_orchestrate:
        response = client.post("/api/v1/audit", json={"url": "https://example.com"})

        assert response.status_code == 403
        assert (
            response.json()["detail"]
            == "All pages on the domain were blocked from crawling. Check robots.txt restrictions."
        )

def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
