from datetime import UTC, datetime

from app.models.comment import Comment
from app.models.group import Group
from app.models.role import Role
from app.models.task import Task
from app.models.user import User


def login(client, name="admin-user"):
    client.cookies.clear()
    response = client.post("/api/auth/login", json={"user_name": name, "password": "test1"})
    assert response.status_code == 200


def worker_comment(client, task=1, parent=None):
    login(client, "takahashi")
    response = client.post(f"/api/tasks/{task}/comments", json={"content": "カテゴリについて質問です", "parent_id": parent})
    assert response.status_code == 201
    return response.json()


def admin_reply(client, parent, task=1):
    login(client)
    response = client.post(f"/api/tasks/{task}/comments", json={"content": "このカテゴリで問題ありません", "parent_id": parent})
    assert response.status_code == 201
    return response.json()


def test_admin_endpoints_require_authentication(client):
    for path in ("/api/admin/overview", "/api/admin/comments", "/api/users/me/replies"):
        assert client.get(path).status_code == 401


def test_worker_cannot_read_admin_progress_or_comments(client):
    login(client, "takahashi")
    assert client.get("/api/admin/overview").status_code == 403
    assert client.get("/api/admin/comments").status_code == 403


def test_progress_counts_active_assignments_and_includes_workers_without_groups(client):
    login(client)
    data = client.get("/api/admin/overview").json()
    assert data["total_tasks"] == 3
    assert data["completed_tasks"] == 1
    assert {worker["user_name"] for worker in data["workers"]} == {"takahashi", "no-groups-user"}
    worker = next(row for row in data["workers"] if row["user_id"] == 1)
    assert worker["group_count"] == 2
    assert worker["total_count"] == 3
    assert worker["completed_count"] == 1
    empty = next(row for row in data["workers"] if row["user_name"] == "no-groups-user")
    assert empty["total_count"] == 0


def test_reply_flow_unanswered_filter_and_worker_inbox(client):
    parent = worker_comment(client)
    login(client)
    pending = client.get("/api/admin/comments?unanswered=true").json()
    assert pending["pagination"]["total"] == 1
    assert pending["comments"][0]["comment_id"] == parent["comment_id"]
    assert client.get("/api/admin/overview").json()["pending_comments"] == 1
    reply = admin_reply(client, parent["comment_id"])
    assert client.get("/api/admin/comments?unanswered=true").json()["pagination"]["total"] == 0
    assert client.get("/api/admin/overview").json()["pending_comments"] == 0
    assert client.get("/api/admin/comments").json()["comments"][0]["has_admin_reply"] is True
    login(client, "takahashi")
    inbox = client.get("/api/users/me/replies").json()
    assert inbox["pagination"]["total"] == 1
    assert inbox["comments"][0]["comment_id"] == reply["comment_id"]
    assert inbox["comments"][0]["parent_content"] == parent["content"]
    assert inbox["comments"][0]["author_role"] == "admin"
    response = client.post("/api/tasks/1/comments", json={"content": "ありがとうございます", "parent_id": reply["comment_id"]})
    assert response.status_code == 201
    login(client)
    assert client.get("/api/admin/comments?unanswered=true").json()["pagination"]["total"] == 1


def test_another_worker_cannot_see_or_forge_access_to_replies(client):
    parent = worker_comment(client)
    admin_reply(client, parent["comment_id"])
    login(client, "no-groups-user")
    assert client.get("/api/users/me/replies?user_id=1").json()["pagination"]["total"] == 0
    assert client.get("/api/tasks/1/comments").status_code == 403
    assert client.post("/api/tasks/1/comments", json={"content": "forged", "parent_id": parent["comment_id"]}).status_code == 403


def test_only_replies_to_existing_same_task_comments_are_accepted(client):
    parent = worker_comment(client)
    login(client)
    response = client.post("/api/tasks/2/comments", json={"content": "wrong task", "parent_id": parent["comment_id"]})
    assert response.status_code == 404


def test_deleted_records_are_not_exposed(client, db_session):
    parent = worker_comment(client)
    reply = admin_reply(client, parent["comment_id"])
    now = datetime.now(UTC).replace(tzinfo=None)
    db_session.get(Comment, parent["comment_id"]).deleted_at = now
    db_session.commit()
    assert client.get("/api/admin/comments").json()["pagination"]["total"] == 0
    login(client, "takahashi")
    item = client.get("/api/users/me/replies").json()["comments"][0]
    assert item["parent_content"] is None
    db_session.get(Task, 1).deleted_at = now
    db_session.commit()
    assert client.get("/api/users/me/replies").json()["pagination"]["total"] == 0


def test_reply_inbox_tracks_current_assignment(client, db_session):
    parent = worker_comment(client)
    admin_reply(client, parent["comment_id"])
    db_session.get(Group, 1).user_id = 3
    db_session.commit()
    login(client, "takahashi")
    assert client.get("/api/users/me/replies").json()["pagination"]["total"] == 0
    login(client, "no-groups-user")
    assert client.get("/api/users/me/replies").json()["pagination"]["total"] == 1


def test_feed_pagination_filters_and_validation(client):
    first = worker_comment(client)
    second = worker_comment(client, task=2)
    login(client)
    data = client.get("/api/admin/comments?page_size=1").json()
    assert data["pagination"]["total"] == 2
    assert data["comments"][0]["comment_id"] == second["comment_id"]
    data = client.get("/api/admin/comments?page_size=1&page=2").json()
    assert data["comments"][0]["comment_id"] == first["comment_id"]
    assert client.get("/api/admin/comments?worker_id=3").json()["pagination"]["total"] == 0
    for query in ("page=0", "page_size=101", "worker_id=0"):
        assert client.get("/api/admin/comments?" + query).status_code == 422


def test_deleted_admin_is_rejected(client, db_session):
    login(client)
    admin = db_session.query(User).filter(User.user_name == "admin-user").one()
    admin.deleted_at = datetime.now(UTC).replace(tzinfo=None)
    db_session.commit()
    assert client.get("/api/admin/overview").status_code == 401
