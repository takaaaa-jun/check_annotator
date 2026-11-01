import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import text


spec = importlib.util.spec_from_file_location("unassign_tasks", Path(__file__).resolve().parents[2] / "scripts/unassign_tasks.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_releases_only_assignment_and_preserves_tasks_comments(db_session, tmp_path):
    connection = db_session.connection()
    before = {table: module.fingerprint(connection, table) for table in ("tasks", "comments")}
    result = module.unassign(connection, tmp_path / "backup.json", 2, "test")
    assert result["released_groups"] == 2
    assert result["remaining_assigned"] == 0
    assert (tmp_path / "backup.json").exists()
    assert before == {table: module.fingerprint(connection, table) for table in before}
    assert connection.execute(text("SELECT user_id FROM `groups` WHERE group_id=3")).scalar_one() == 1  # deleted group remains unchanged


def test_wrong_count_and_existing_backup_prevent_changes(db_session, tmp_path):
    connection = db_session.connection()
    with pytest.raises(RuntimeError):
        module.unassign(connection, tmp_path / "new.json", 999, "test")
    path = tmp_path / "existing.json"
    path.write_text("keep", encoding="utf-8")
    with pytest.raises(FileExistsError):
        module.unassign(connection, path, 2, "test")
    assert connection.execute(text("SELECT user_id FROM `groups` WHERE group_id=1")).scalar_one() == 1
