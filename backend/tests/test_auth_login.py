import jwt
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import JWT_ALGORITHM
from app.models.user import User


def test_login_returns_user_and_sets_cookie(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": "takahashi", "password": "test1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user": {
            "user_id": 1,
            "user_name": "takahashi",
            "role_name": "worker",
        }
    }

    cookie = response.cookies.get("access_token")
    assert cookie is not None
    payload = jwt.decode(
        cookie,
        "test-secret-key-for-login-tests-2026",
        algorithms=[JWT_ALGORITHM],
    )
    assert payload["sub"] == "1"
    assert "iat" in payload
    assert "exp" in payload

    set_cookie = response.headers["set-cookie"].lower()
    assert "max-age=28800" in set_cookie
    assert "path=/" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "httponly" not in set_cookie
    assert "secure" not in set_cookie


def test_login_updates_login_at(client: TestClient, db_session: Session) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": "takahashi", "password": "test1"},
    )

    assert response.status_code == 200
    user = db_session.scalar(select(User).where(User.user_name == "takahashi"))
    assert user is not None
    db_session.refresh(user)
    assert user.login_at is not None


def test_login_rejects_wrong_password(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": "takahashi", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": {
            "code": "INVALID_CREDENTIALS",
            "message": "ユーザー名またはパスワードが正しくありません",
        }
    }


def test_login_rejects_unknown_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": "unknown", "password": "test1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_deleted_user(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": "deleted-user", "password": "test1"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_rejects_invalid_request(client: TestClient) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": "takahashi"},
    )

    assert response.status_code == 422
    assert response.json() == {
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "入力値が正しくありません",
        }
    }
