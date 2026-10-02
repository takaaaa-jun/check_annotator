from fastapi.testclient import TestClient


def login(
    client: TestClient,
    user_name: str = "takahashi",
) -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": user_name, "password": "test1"},
    )
    assert response.status_code == 200


def test_get_user_groups_returns_progress(client: TestClient) -> None:
    login(client)

    response = client.get("/api/users/1/groups")

    assert response.status_code == 200
    assert response.json() == {
        "user": {"user_id": 1, "user_name": "takahashi"},
        "groups": [
            {
                "group_id": 1,
                "group_name": "グループ1",
                "image_id_min": 10,
                "image_id_max": 20,
                "total_count": 3,
                "state_counts": [
                    {"state_id": 1, "state_name": "未着手", "count": 2},
                    {"state_id": 2, "state_name": "完了", "count": 1},
                    {"state_id": 3, "state_name": "付与予定ラベル", "count": 0},
                    {"state_id": 4, "state_name": "コメント", "count": 0},
                ],
            },
            {
                "group_id": 2,
                "group_name": "空グループ",
                "image_id_min": None,
                "image_id_max": None,
                "total_count": 0,
                "state_counts": [
                    {"state_id": 1, "state_name": "未着手", "count": 0},
                    {"state_id": 2, "state_name": "完了", "count": 0},
                    {"state_id": 3, "state_name": "付与予定ラベル", "count": 0},
                    {"state_id": 4, "state_name": "コメント", "count": 0},
                ],
            },
        ],
    }


def test_get_user_groups_returns_empty_list(client: TestClient) -> None:
    login(client, "no-groups-user")

    response = client.get("/api/users/3/groups")

    assert response.status_code == 200
    assert response.json() == {
        "user": {"user_id": 3, "user_name": "no-groups-user"},
        "groups": [],
    }


def test_get_user_groups_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/users/1/groups")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"


def test_worker_cannot_get_other_user_groups(client: TestClient) -> None:
    login(client)

    response = client.get("/api/users/3/groups")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_can_get_other_user_groups(client: TestClient) -> None:
    login(client, "admin-user")

    response = client.get("/api/users/1/groups")

    assert response.status_code == 200
    assert response.json()["user"]["user_id"] == 1


def test_admin_gets_404_for_unknown_user(client: TestClient) -> None:
    login(client, "admin-user")

    response = client.get("/api/users/999/groups")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"


def test_admin_gets_404_for_deleted_user(client: TestClient) -> None:
    login(client, "admin-user")

    response = client.get("/api/users/2/groups")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "USER_NOT_FOUND"
