from fastapi.testclient import TestClient
import pytest

from app.core.security import get_auth_secret_key


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_contains_all_backend_endpoints(client: TestClient) -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    paths = response.json()["paths"]
    assert {
        "/api/auth/login",
        "/api/auth/logout",
        "/api/users/me",
        "/api/users/{user_id}/groups",
        "/api/users/{user_id}/groups/{group_id}/tasks",
        "/api/tasks/{task_id}/state",
        "/api/tasks/{task_id}/comments",
        "/health",
    }.issubset(paths)
    assert "post" in paths["/api/tasks/{task_id}/comments"]
    assert "get" in paths["/api/tasks/{task_id}/comments"]


def test_cors_allows_frontend_credentials(client: TestClient) -> None:
    response = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_empty_auth_secret_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AUTH_SECRET_KEY", "")
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY must be configured"):
        get_auth_secret_key()
