from fastapi.testclient import TestClient


def login(client: TestClient, user_name: str = "takahashi") -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": user_name, "password": "test1"},
    )
    assert response.status_code == 200


def test_get_group_tasks(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/1/groups/1/tasks?page_size=10")
    assert response.status_code == 200
    body = response.json()
    assert body["group"] == {
        "group_id": 1, "group_name": "グループ1", "user_id": 1,
        "user_name": "takahashi",
    }
    assert [task["image_id"] for task in body["tasks"]] == [10, 11, 20]
    assert all(task["updated_at"].endswith("Z") for task in body["tasks"])
    assert body["pagination"] == {
        "page": 1, "page_size": 10, "total": 3, "total_pages": 1,
    }


def test_filter_group_tasks_by_state(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/1/groups/1/tasks?state_id=1&page_size=10")
    assert response.status_code == 200
    assert [task["image_id"] for task in response.json()["tasks"]] == [10, 11]
    assert response.json()["pagination"]["total"] == 2


def test_group_tasks_pagination(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/1/groups/1/tasks?page=2&page_size=10")
    assert response.status_code == 200
    assert response.json()["tasks"] == []
    assert response.json()["pagination"] == {
        "page": 2, "page_size": 10, "total": 3, "total_pages": 1,
    }


def test_empty_group_tasks(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/1/groups/2/tasks")
    assert response.status_code == 200
    assert response.json()["tasks"] == []
    assert response.json()["pagination"]["total_pages"] == 0


def test_group_tasks_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/users/1/groups/1/tasks")
    assert response.status_code == 401


def test_worker_cannot_get_other_groups(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/3/groups/1/tasks")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_can_get_group_tasks(client: TestClient) -> None:
    login(client, "admin-user")
    response = client.get("/api/users/1/groups/1/tasks")
    assert response.status_code == 200


def test_unknown_group_returns_404(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/1/groups/999/tasks")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "GROUP_NOT_FOUND"


def test_unknown_state_returns_404(client: TestClient) -> None:
    login(client)
    response = client.get("/api/users/1/groups/1/tasks?state_id=999")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "STATE_NOT_FOUND"


def test_invalid_query_returns_422(client: TestClient) -> None:
    login(client)
    for query in ["page=0", "page_size=20", "state_id=0"]:
        response = client.get(f"/api/users/1/groups/1/tasks?{query}")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
