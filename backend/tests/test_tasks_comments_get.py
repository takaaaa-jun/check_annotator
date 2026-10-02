from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.comment import Comment


def login(client: TestClient, user_name: str = "takahashi") -> None:
    response = client.post(
        "/api/auth/login",
        json={"user_name": user_name, "password": "test1"},
    )
    assert response.status_code == 200


def add_comments(db: Session, count: int, task_id: int = 1) -> list[Comment]:
    base = datetime.now(UTC).replace(tzinfo=None)
    comments = [
        Comment(
            task_id=task_id,
            user_id=1,
            parent_id=None,
            content=f"コメント{i}",
            created_at=base + timedelta(seconds=i // 2),
            updated_at=base + timedelta(seconds=i // 2),
            deleted_at=None,
        )
        for i in range(count)
    ]
    db.add_all(comments)
    db.commit()
    return comments


def test_get_assigned_task_comments_in_stable_order(
    client: TestClient,
    db_session: Session,
) -> None:
    comments = add_comments(db_session, 3)
    login(client)
    response = client.get("/api/tasks/1/comments")
    assert response.status_code == 200
    body = response.json()
    assert body["task_id"] == 1
    assert [item["comment_id"] for item in body["comments"]] == [
        comment.comment_id for comment in comments
    ]
    assert body["comments"][0]["user_name"] == "takahashi"
    assert body["comments"][0]["created_at"].endswith("Z")
    assert body["pagination"] == {
        "page": 1,
        "page_size": 50,
        "total": 3,
        "total_pages": 1,
    }


def test_admin_can_get_any_task_comments(
    client: TestClient,
    db_session: Session,
) -> None:
    add_comments(db_session, 1)
    login(client, "admin-user")
    response = client.get("/api/tasks/1/comments")
    assert response.status_code == 200
    assert len(response.json()["comments"]) == 1


def test_get_comments_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/tasks/1/comments")
    assert response.status_code == 401


def test_worker_cannot_get_other_task_comments(client: TestClient) -> None:
    login(client, "no-groups-user")
    response = client.get("/api/tasks/1/comments")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PERMISSION_DENIED"


def test_unknown_or_deleted_task_returns_404(client: TestClient) -> None:
    login(client)
    for task_id in [4, 999]:
        response = client.get(f"/api/tasks/{task_id}/comments")
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "TASK_NOT_FOUND"


def test_comment_pagination(client: TestClient, db_session: Session) -> None:
    comments = add_comments(db_session, 11)
    login(client)
    response = client.get("/api/tasks/1/comments?page=2&page_size=10")
    assert response.status_code == 200
    body = response.json()
    assert [item["comment_id"] for item in body["comments"]] == [comments[10].comment_id]
    assert body["pagination"] == {
        "page": 2,
        "page_size": 10,
        "total": 11,
        "total_pages": 2,
    }


def test_no_comments_returns_empty_list(client: TestClient) -> None:
    login(client)
    response = client.get("/api/tasks/1/comments")
    assert response.status_code == 200
    assert response.json()["comments"] == []
    assert response.json()["pagination"]["total_pages"] == 0


def test_deleted_comments_are_excluded(client: TestClient, db_session: Session) -> None:
    comments = add_comments(db_session, 2)
    comments[0].deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db_session.commit()
    login(client)
    response = client.get("/api/tasks/1/comments")
    assert response.status_code == 200
    assert [item["comment_id"] for item in response.json()["comments"]] == [
        comments[1].comment_id
    ]
    assert response.json()["pagination"]["total"] == 1


def test_invalid_pagination_returns_422(client: TestClient) -> None:
    login(client)
    for query in ["page=0", "page_size=0", "page_size=20", "page_size=invalid"]:
        response = client.get(f"/api/tasks/1/comments?{query}")
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
