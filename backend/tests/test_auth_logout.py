from fastapi.testclient import TestClient


def test_logout_deletes_access_token_cookie(
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
    assert client.cookies.get("access_token") is not None

    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert response.content == b""
    assert client.cookies.get("access_token") is None

    set_cookie = response.headers["set-cookie"].lower()
    assert "access_token=" in set_cookie
    assert "max-age=0" in set_cookie
    assert "path=/" in set_cookie
    assert "samesite=lax" in set_cookie

    authenticated_response = client.get("/api/users/me")

    assert authenticated_response.status_code == 401
    assert authenticated_response.json() == {
        "error": {
            "code": "AUTHENTICATION_REQUIRED",
            "message": "認証が必要です",
        }
    }


def test_logout_without_cookie_is_successful(
    client: TestClient,
) -> None:
    response = client.post("/api/auth/logout")

    assert response.status_code == 204
    assert response.content == b""

    set_cookie = response.headers["set-cookie"].lower()
    assert "access_token=" in set_cookie
    assert "max-age=0" in set_cookie
    assert "path=/" in set_cookie
    assert "samesite=lax" in set_cookie
