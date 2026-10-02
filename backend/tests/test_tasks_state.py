from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.models.task import Task
from app.repositories.task_repository import TaskRepository


def login(client: TestClient, user_name: str = "takahashi") -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": user_name, "password": "test1"},
    )
    assert response.status_code == 200


def test_update_task_state(client: TestClient) -> None:
    login(client)
    response = client.patch("/api/tasks/1/state", json={"state_id": 2})
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 1
    assert body["group_id"] == 1
    assert body["image_id"] == 10
    assert body["state_id"] == 2
    assert body["state_name"] == "完了"
    assert body["updated_at"].endswith("Z")

    tasks_response = client.get("/api/users/1/groups/1/tasks?state_id=2")
    assert tasks_response.status_code == 200
    assert 10 in [task["image_id"] for task in tasks_response.json()["tasks"]]


def test_update_task_state_requires_authentication(client: TestClient) -> None:
    response = client.patch("/api/tasks/1/state", json={"state_id": 2})
    assert response.status_code == 401


def test_worker_cannot_update_other_task(client: TestClient) -> None:
    login(client, "no-groups-user")
    response = client.patch("/api/tasks/1/state", json={"state_id": 2})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_can_update_task(client: TestClient) -> None:
    login(client, "admin-user")
    response = client.patch("/api/tasks/1/state", json={"state_id": 2})
    assert response.status_code == 200


def test_unknown_task_returns_404(client: TestClient) -> None:
    login(client)
    response = client.patch("/api/tasks/999/state", json={"state_id": 2})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_deleted_task_returns_404(client: TestClient) -> None:
    login(client)
    response = client.patch("/api/tasks/4/state", json={"state_id": 2})
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_unknown_or_deleted_state_returns_404(client: TestClient) -> None:
    login(client)
    for state_id in [5, 999]:
        response = client.patch("/api/tasks/1/state", json={"state_id": state_id})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "STATE_NOT_FOUND"


def test_invalid_request_returns_422(client: TestClient) -> None:
    login(client)
    for payload in [{}, {"state_id": 0}, {"state_id": "invalid"}]:
        response = client.patch("/api/tasks/1/state", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_update_task_state_rolls_back_on_commit_failure() -> None:
    db = Mock()
    db.scalar.return_value = "完了"
    db.commit.side_effect = RuntimeError("commit failed")
    task = Task(
        task_id=1,
        group_id=1,
        image_id=10,
        state_id=1,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        updated_at=datetime.now(UTC).replace(tzinfo=None),
        deleted_at=None,
    )

    with pytest.raises(RuntimeError, match="commit failed"):
        TaskRepository(db).update_state(
            task,
            state_id=2,
            updated_at=datetime.now(UTC).replace(tzinfo=None),
        )

    db.rollback.assert_called_once_with()
    db.refresh.assert_not_called()
