from sqlalchemy import select
from app.models.group import Group
from app.models.task import Task
from app.models.comment import Comment
from test_assignments import login

URL = "/api/admin/assignment-ranges"


def current(client):
    return client.get(URL).json()


def save(client, ranges, revision=None):
    return client.post(URL, json={"revision": revision or current(client)["revision"], "ranges": ranges})


def row(start=10, end=11, owner=3):
    return dict(start_image_id=start, end_image_id=end, user_id=owner)


def test_permissions(client):
    assert client.get(URL).status_code == 401
    login(client, "takahashi")
    assert client.get(URL).status_code == 403
    assert save(client, [], "a" * 64).status_code == 403


def test_repartition_preserves_tasks_comments_and_changes_access(client, db_session):
    login(client, "takahashi")
    comment = client.post("/api/tasks/1/comments", json={"content": "範囲変更後も保持", "parent_id": None}).json()
    before = [(t.task_id, t.image_id, t.state_id, t.created_at, t.updated_at, t.deleted_at) for t in db_session.scalars(select(Task))]
    login(client)
    response = save(client, [row()])
    assert response.status_code == 200
    assert response.json()["ranges"] == [row()]
    db_session.expire_all()
    after = [(t.task_id, t.image_id, t.state_id, t.created_at, t.updated_at, t.deleted_at) for t in db_session.scalars(select(Task))]
    assert before == after
    assert db_session.get(Comment, comment["comment_id"]).content == "範囲変更後も保持"
    assert db_session.get(Group, 1).deleted_at is not None
    assert db_session.get(Group, 2).deleted_at is not None
    task = db_session.get(Task, 3)
    assert db_session.get(Group, task.group_id).user_id is None
    login(client, "takahashi")
    assert client.get("/api/tasks/1/comments").status_code == 403
    login(client, "no-groups-user")
    assert client.get("/api/tasks/1/comments").status_code == 200


def test_rejects_overlap_reverse_missing_and_duplicates_without_mutation(client, db_session):
    login(client)
    revision = current(client)["revision"]
    for ranges in ([row(11, 10)], [row(), row(11, 11)], [row(10, 20)], [row(99, 100)]):
        assert save(client, ranges, revision).status_code == 409
        assert current(client)["revision"] == revision
    task = db_session.get(Task, 3)
    task.image_id = 10
    db_session.commit()
    assert save(client, [row()]).status_code == 409


def test_conflicting_revision_and_legacy_owner_update(client, db_session):
    login(client)
    revision = current(client)["revision"]
    db_session.get(Group, 1).user_id = None
    db_session.commit()
    assert save(client, [row()], revision).status_code == 409
    assert db_session.get(Group, 1).user_id is None


def test_clear_reuse_range_name_and_multiple_ranges(client, db_session):
    login(client)
    first = save(client, [row(), row(20, 20, 1)])
    assert first.status_code == 200
    stale = first.json()["revision"]
    assert save(client, []).status_code == 200
    assert current(client)["ranges"] == []
    assert save(client, [row()], stale).status_code == 409
    assert save(client, [row(10, 11, 1)]).status_code == 200
    active = list(db_session.scalars(select(Group).where(Group.deleted_at.is_(None))))
    assert {g.group_name for g in active} == {"00010-00011", "未割り当て"}


def test_invalid_users_and_strict_ids(client):
    login(client)
    assert save(client, [row(owner=4)]).status_code == 403
    assert save(client, [row(owner=2)]).status_code == 404
    for invalid in (row(0, 11), row(True, 11), row(10, 4294967296), row(owner=None)):
        assert save(client, [invalid]).status_code == 422


def test_target_changes_invalidate_revision_but_progress_does_not(client, db_session):
    login(client)
    revision = current(client)["revision"]
    db_session.get(Task, 1).state_id = 2
    db_session.commit()
    assert save(client, [row()], revision).status_code == 200
    revision = current(client)["revision"]
    db_session.get(Task, 1).image_id = 12
    db_session.commit()
    assert save(client, [], revision).status_code == 409
