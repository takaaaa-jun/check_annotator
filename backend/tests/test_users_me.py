from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from app.core.security import JWT_ALGORITHM


TEST_SECRET_KEY = (
    "test-secret-key-for-login-tests-2026"
)


def create_test_token(
    user_id: int | str,
    *,
    expires_at: datetime | None = None,
    include_subject: bool = True,
    secret_key: str = TEST_SECRET_KEY,
) -> str:
    now = datetime.now(UTC)

    payload = {
        "iat": now,
        "exp": expires_at
        or now + timedelta(hours=8),
    }

    if include_subject:
        payload["sub"] = str(user_id)

    return jwt.encode(
        payload,
        secret_key,
        algorithm=JWT_ALGORITHM,
    )


def test_get_current_user_returns_user(
    client: TestClient,
) -> None:
    login_response = client.post(
        "/api/auth/login",
        json={
            "user_name": "takahashi",
            "password": "test1",
        },
    )

    assert login_response.status_code == 200
    assert (
        client.cookies.get("access_token")
        is not None
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 200

    body = response.json()

    assert body["user_id"] == 1
    assert body["user_name"] == "takahashi"
    assert body["role_id"] == 1
    assert body["role_name"] == "worker"
    assert body["login_at"] is not None
    assert body["login_at"].endswith("Z")


def test_get_current_user_requires_cookie(
    client: TestClient,
) -> None:
    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "認証が必要です",
        }
    }


def test_get_current_user_rejects_invalid_token(
    client: TestClient,
) -> None:
    client.cookies.set(
        "access_token",
        "invalid-token",
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )


def test_get_current_user_rejects_wrong_signature(
    client: TestClient,
) -> None:
    token = create_test_token(
        1,
        secret_key=(
            "different-secret-key-for-test-2026"
        ),
    )
    client.cookies.set(
        "access_token",
        token,
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )


def test_get_current_user_rejects_expired_token(
    client: TestClient,
) -> None:
    token = create_test_token(
        1,
        expires_at=(
            datetime.now(UTC)
            - timedelta(seconds=1)
        ),
    )
    client.cookies.set(
        "access_token",
        token,
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )


def test_get_current_user_rejects_missing_subject(
    client: TestClient,
) -> None:
    token = create_test_token(
        1,
        include_subject=False,
    )
    client.cookies.set(
        "access_token",
        token,
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )


def test_get_current_user_rejects_invalid_subject(
    client: TestClient,
) -> None:
    token = create_test_token(
        "not-a-user-id",
    )
    client.cookies.set(
        "access_token",
        token,
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )


def test_get_current_user_rejects_unknown_user(
    client: TestClient,
) -> None:
    token = create_test_token(
        999,
    )
    client.cookies.set(
        "access_token",
        token,
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )


def test_get_current_user_rejects_deleted_user(
    client: TestClient,
) -> None:
    token = create_test_token(
        2,
    )
    client.cookies.set(
        "access_token",
        token,
    )

    response = client.get(
        "/api/users/me"
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == (
        "AUTHENTICATION_REQUIRED"
    )