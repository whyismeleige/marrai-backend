import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, Mock

from main import app
import app.api.dependencies as dependencies
from app.api.routes import audit as audit_routes
from tests.fakes import FakeRedis
from tests.fixtures import fake_job_id

# NOTE: TestClient used WITHOUT the context manager so the FastAPI lifespan
# (which dials real PostgreSQL/Redis) does not run. Shared route dependencies
# are mocked per test instead.

client = TestClient(app)


def _fake_task():
    return type("FakeTask", (), {"delay": Mock(return_value=None)})()


@pytest.fixture(autouse=True)
def _isolate_rate_limiter():
    """Every test in this module bypasses the Redis-backed rate limiter."""
    app.dependency_overrides[dependencies.rate_limit_check] = lambda: "127.0.0.1"
    yield
    app.dependency_overrides.pop(dependencies.rate_limit_check, None)


@pytest.fixture
def safe_url_check(monkeypatch):
    mocked = AsyncMock()
    monkeypatch.setattr(audit_routes, "assert_url_safe", mocked)
    return mocked


def _post_audit(path="/api/v1/audit", payload=None, **kwargs):
    return client.post(
        path,
        json=payload or {"url": "https://example.com", "email": "sample@example.com"},
        **kwargs,
    )


def test_successful_job_creation(monkeypatch, safe_url_check):
    monkeypatch.setattr(audit_routes, "create_job", AsyncMock(return_value=fake_job_id))
    run_task_mock = _fake_task()
    monkeypatch.setattr(audit_routes, "run_audit_task", run_task_mock)

    response = _post_audit()

    assert response.status_code == 200
    assert response.json()["job_id"] == fake_job_id
    run_task_mock.delay.assert_called_once_with(
        fake_job_id, "https://example.com/", "sample@example.com"
    )


def test_email_is_optional(monkeypatch, safe_url_check):
    create_mock = AsyncMock(return_value=fake_job_id)
    monkeypatch.setattr(audit_routes, "create_job", create_mock)
    monkeypatch.setattr(audit_routes, "run_audit_task", _fake_task())

    response = _post_audit(payload={"url": "https://example.com"})

    assert response.status_code == 200
    assert create_mock.await_args.args[1] is None


def test_malformed_seed_url(monkeypatch, safe_url_check):
    response = _post_audit(payload={"url": "abcd", "email": "sample@example.com"})
    assert response.status_code == 422


def test_invalid_email(monkeypatch, safe_url_check):
    response = _post_audit(
        payload={"url": "https://example.com", "email": "invalid-email"}
    )
    assert response.status_code == 422


def test_private_url_rejected(monkeypatch, safe_url_check):
    from app.core.errors import UrlSafetyError

    safe_url_check.side_effect = UrlSafetyError(
        "This website resolves to a private network and cannot be audited."
    )

    response = _post_audit()

    assert response.status_code == 400
    assert "private" in response.json()["detail"]


def test_run_audit_server_error(monkeypatch, safe_url_check):
    monkeypatch.setattr(
        audit_routes, "create_job", AsyncMock(side_effect=Exception("DB Error"))
    )

    response = _post_audit()

    assert response.status_code == 500
    assert "Something went wrong" in response.json()["detail"]


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_endpoint_without_infrastructure():
    # With no DB/Redis running, readiness must report unavailable, not crash.
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "unavailable"


def _enable_real_rate_limiter(monkeypatch) -> FakeRedis:
    """Swap the mocked rate limiter for the real one backed by FakeRedis."""
    app.dependency_overrides.pop(dependencies.rate_limit_check, None)
    fake_redis = FakeRedis()

    async def fake_client_factory():
        return fake_redis

    monkeypatch.setattr(dependencies, "get_redis_client", fake_client_factory)
    return fake_redis


def test_proxy_secret_required_when_configured(monkeypatch, safe_url_check):
    _enable_real_rate_limiter(monkeypatch)
    monkeypatch.setattr(dependencies.settings, "API_PROXY_SHARED_SECRET", "test-secret")
    try:
        response = _post_audit()
        assert response.status_code == 403
    finally:
        monkeypatch.setattr(dependencies.settings, "API_PROXY_SHARED_SECRET", "")


def test_proxy_secret_gates_forwarded_ip(monkeypatch, safe_url_check):
    _enable_real_rate_limiter(monkeypatch)
    create_mock = AsyncMock(return_value=fake_job_id)
    monkeypatch.setattr(audit_routes, "create_job", create_mock)
    monkeypatch.setattr(audit_routes, "run_audit_task", _fake_task())
    monkeypatch.setattr(dependencies.settings, "API_PROXY_SHARED_SECRET", "test-secret")
    try:
        response = _post_audit(
            headers={"X-Proxy-Secret": "test-secret", "X-Client-IP": "1.2.3.4"}
        )
        assert response.status_code == 200
        assert response.json()["job_id"] == fake_job_id
    finally:
        monkeypatch.setattr(dependencies.settings, "API_PROXY_SHARED_SECRET", "")


def test_spoofed_ip_header_ignored_without_secret(monkeypatch, safe_url_check):
    create_mock = AsyncMock(return_value=fake_job_id)
    monkeypatch.setattr(audit_routes, "create_job", create_mock)
    monkeypatch.setattr(audit_routes, "run_audit_task", _fake_task())
    # Without a shared secret the X-Client-IP header must be ignored; the
    # request still succeeds, rate limited by the direct peer IP.
    response = _post_audit(headers={"X-Client-IP": "203.0.113.66"})
    assert response.status_code == 200


def test_job_found(monkeypatch):
    from tests.fixtures import fake_successful_job_response

    monkeypatch.setattr(
        audit_routes, "get_job", AsyncMock(return_value=fake_successful_job_response)
    )
    response = client.get(f"/api/v1/audit/{fake_job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["job_id"] == fake_job_id


def test_job_not_found(monkeypatch):
    monkeypatch.setattr(audit_routes, "get_job", AsyncMock(return_value=None))
    response = client.get(f"/api/v1/audit/{fake_job_id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "Audit job was not found."


def test_malformed_job_id_is_422(monkeypatch):
    monkeypatch.setattr(audit_routes, "get_job", AsyncMock())
    response = client.get("/api/v1/audit/not-a-real-uuid")
    assert response.status_code == 422


def test_get_audit_server_error(monkeypatch):
    monkeypatch.setattr(audit_routes, "get_job", AsyncMock(side_effect=Exception("boom")))
    response = client.get(f"/api/v1/audit/{fake_job_id}")
    assert response.status_code == 500
    assert "Something went wrong" in response.json()["detail"]


def test_rate_limiter_blocks_abuse(monkeypatch, safe_url_check):
    _enable_real_rate_limiter(monkeypatch)
    monkeypatch.setattr(audit_routes, "create_job", AsyncMock(return_value=fake_job_id))
    monkeypatch.setattr(audit_routes, "run_audit_task", _fake_task())

    limit = dependencies.settings.RATE_LIMIT_MAX_REQUESTS
    for attempt in range(limit + 1):
        response = _post_audit()
        if response.status_code == 429:
            assert attempt == limit
            assert "Retry-After" in response.headers
            return
    raise AssertionError("Rate limit never applied")