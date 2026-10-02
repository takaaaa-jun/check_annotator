from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.models.comment import Comment
from app.repositories.comment_repository import CommentRepository


def login(client: TestClient, user_name: str = "takahashi") -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": user_name, "password": "test1"},
    )
    assert response.status_code == 200


def test_create_comment_trims_content(client: TestClient) -> None:
    login(client)
    response = client.post(
        "/api/tasks/1/comments",
        json={"content": "  付与予定ラベル: tuna  ", "parent_id": None},
    )
    assert response.status_code == 201
    assert response.json() == {
        "comment_id": 1,
        "task_id": 1,
        "user_id": 1,
        "user_name": "takahashi",
        "parent_id": None,
        "content": "付与予定ラベル: tuna",
        "created_at": response.json()["created_at"],
        "updated_at": response.json()["updated_at"],
    }
    assert response.json()["created_at"].endswith("Z")
    assert response.json()["updated_at"].endswith("Z")


def test_create_reply(client: TestClient) -> None:
    login(client)
    parent = client.post("/api/tasks/1/comments", json={"content": "親コメント"})
    response = client.post(
        "/api/tasks/1/comments",
        json={"content": "返信", "parent_id": parent.json()["comment_id"]},
    )
    assert response.status_code == 201
    assert response.json()["parent_id"] == parent.json()["comment_id"]


def test_create_comment_requires_authentication(client: TestClient) -> None:
    response = client.post("/api/tasks/1/comments", json={"content": "コメント"})
    assert response.status_code == 401


def test_worker_cannot_comment_on_other_task(client: TestClient) -> None:
    login(client, "no-groups-user")
    response = client.post("/api/tasks/1/comments", json={"content": "コメント"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_admin_can_comment_on_any_task(client: TestClient) -> None:
    login(client, "admin-user")
    response = client.post("/api/tasks/1/comments", json={"content": "管理者コメント"})
    assert response.status_code == 201
    assert response.json()["user_name"] == "admin-user"


def test_unknown_or_deleted_task_returns_404(client: TestClient) -> None:
    login(client)
    for task_id in [4, 999]:
        response = client.post(f"/api/tasks/{task_id}/comments", json={"content": "コメント"})
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_unknown_parent_returns_404(client: TestClient) -> None:
    login(client)
    response = client.post(
        "/api/tasks/1/comments",
        json={"content": "返信", "parent_id": 999},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMMENT_NOT_FOUND"


def test_parent_for_another_task_returns_404(client: TestClient) -> None:
    login(client)
    parent = client.post("/api/tasks/1/comments", json={"content": "親コメント"})
    response = client.post(
        "/api/tasks/2/comments",
        json={"content": "返信", "parent_id": parent.json()["comment_id"]},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "COMMENT_NOT_FOUND"


def test_invalid_content_returns_422(client: TestClient) -> None:
    login(client)
    for payload in [{}, {"content": "   "}, {"content": "x" * 2001}]:
        response = client.post("/api/tasks/1/comments", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_create_comment_rolls_back_on_commit_failure() -> None:
    db = Mock()
    db.commit.side_effect = RuntimeError("commit failed")

    with pytest.raises(RuntimeError, match="commit failed"):
        CommentRepository(db).create(
            task_id=1,
            user_id=1,
            parent_id=None,
            content="コメント",
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )

    db.rollback.assert_called_once_with()
    db.refresh.assert_not_called()
