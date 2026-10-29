"""初期化ツールのAPI検証を既存のSQLiteテストDBで確認する。"""
import importlib.util
from pathlib import Path

from sqlalchemy import select, update

from app.models.role import Role
from app.models.user import User


def test_initialization_api_checks(monkeypatch, db_session, client):
    import app.database
    import app.main

    engine = db_session.get_bind()
    monkeypatch.setattr(app.database, "engine", engine)
    monkeypatch.setattr(app.main, "check_database_connection", lambda: app.database.check_database_connection(engine))
    admin_id = db_session.scalar(select(Role.role_id).where(Role.role_name == "admin"))
    db_session.execute(update(User).where(User.user_name == "takahashi").values(role_id=admin_id))
    db_session.commit()
    path = Path(__file__).resolve().parents[2] / "scripts" / "initialize_database.py"
    spec = importlib.util.spec_from_file_location("initialization_api_checks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify_api()
