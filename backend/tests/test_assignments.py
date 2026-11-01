from datetime import UTC, datetime
from sqlalchemy import select
from app.models.group import Group
from app.models.task import Task
from app.models.comment import Comment


def login(client, name="admin-user"):
    client.cookies.clear()
    assert client.post("/api/auth/login", json={"user_name": name, "password": "test1"}).status_code == 200


def save(client, items):
    return client.post("/api/admin/assignments", json={"assignments": items})


def test_assignment_permissions(client):
    assert client.get("/api/admin/assignments").status_code == 401
    login(client, "takahashi")
    assert client.get("/api/admin/assignments").status_code == 403
    assert save(client, [{"group_id": 1, "user_id": None, "expected_user_id": 1}]).status_code == 403


def test_unassign_and_reassign_preserve_work_and_access(client, db_session):
    login(client, "takahashi")
    parent = client.post("/api/tasks/1/comments", json={"content": "残すコメント", "parent_id": None}).json()
    tasks_before = [(task.task_id, task.group_id, task.state_id, task.updated_at) for task in db_session.scalars(select(Task))]
    login(client)
    result = save(client, [{"group_id": 1, "user_id": None, "expected_user_id": 1}])
    assert result.status_code == 200
    group = next(row for row in result.json()["groups"] if row["group_id"] == 1)
    assert group["user_id"] is None and group["total_count"] == 3
    assert client.get("/api/admin/overview").json()["unassigned_tasks"] == 3
    result = save(client, [{"group_id": 1, "user_id": 3, "expected_user_id": None}])
    assert result.status_code == 200
    db_session.expire_all()
    assert tasks_before == [(task.task_id, task.group_id, task.state_id, task.updated_at) for task in db_session.scalars(select(Task))]
    assert db_session.get(Comment, parent["comment_id"]).content == "残すコメント"
    login(client, "takahashi")
    assert client.get("/api/tasks/1/comments").status_code == 403
    login(client, "no-groups-user")
    assert client.get("/api/tasks/1/comments").status_code == 200


def test_conflict_rolls_back_entire_batch(client, db_session):
    login(client)
    result = save(client, [{"group_id": 1, "user_id": 3, "expected_user_id": 1}, {"group_id": 2, "user_id": 3, "expected_user_id": None}])
    assert result.status_code == 409
    db_session.expire_all()
    assert db_session.get(Group, 1).user_id == 1
    assert db_session.get(Group, 2).user_id == 1


def test_rejects_duplicates_admin_deleted_users_and_deleted_groups(client, db_session):
    login(client)
    item = {"group_id": 1, "user_id": 3, "expected_user_id": 1}
    assert save(client, [item, item]).status_code == 409
    assert save(client, [dict(item, user_id=4)]).status_code == 403
    assert save(client, [dict(item, user_id=2)]).status_code == 404
    assert save(client, [dict(item, group_id=3)]).status_code == 404
    assert db_session.get(Group, 1).user_id == 1


def test_requires_expected_owner_and_valid_positive_ids(client):
    login(client)
    assert save(client, []).status_code == 422
    for item in ({"group_id": 1, "user_id": 3}, {"group_id": True, "user_id": 3, "expected_user_id": 1}, {"group_id": 1, "user_id": 0, "expected_user_id": 1}):
        assert save(client, [item]).status_code == 422


def test_assignment_list_includes_unassigned_and_empty_groups(client, db_session):
    db_session.get(Group, 1).user_id = None
    db_session.commit()
    login(client)
    data = client.get("/api/admin/assignments").json()
    assert len(data["groups"]) == 2
    first = data["groups"][0]
    assert first["user_id"] is None and first["image_id_min"] == 10 and first["image_id_max"] == 20
    assert data["groups"][1]["total_count"] == 0
