import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.user import User

path = Path(__file__).resolve().parents[2] / "scripts/set_user_password.py"
spec = importlib.util.spec_from_file_location("set_user_password", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_password_confirmation_mismatch():
    values = iter(["first-long-password", "other-long-password"])
    with pytest.raises(RuntimeError, match="一致しません"):
        module.read_password(lambda _: next(values))


def test_short_password_rejected():
    with pytest.raises(RuntimeError, match="8文字"):
        module.read_password(lambda _: "1234567")


def test_eight_character_password_accepted():
    assert module.read_password(lambda _: "test1234") == "test1234"


def test_initial_password_hash_and_login(db_session, client):
    user = db_session.scalar(select(User).where(User.user_name == "takahashi"))
    user.password_hash = "!"
    db_session.commit()
    module.set_initial_password(db_session, "takahashi", "test1234")
    db_session.refresh(user)
    assert user.password_hash != "test1234"
    assert verify_password("test1234", user.password_hash)
    response = client.post("/api/auth/login", json={
        "user_name": "takahashi", "password": "test1234",
    })
    assert response.status_code == 200
    assert client.get("/api/users/me").status_code == 200


def test_existing_password_is_preserved(db_session):
    user = db_session.scalar(select(User).where(User.user_name == "takahashi"))
    original = user.password_hash
    with pytest.raises(RuntimeError, match="上書きしません"):
        module.set_initial_password(db_session, "takahashi", "test-only-new-password")
    db_session.refresh(user)
    assert user.password_hash == original


def test_missing_user_is_not_created(db_session):
    with pytest.raises(RuntimeError, match="見つかりません"):
        module.set_initial_password(db_session, "nonexistent", "test-only-new-password")
    assert db_session.scalar(select(User).where(User.user_name == "nonexistent")) is None


def test_database_error_shows_code_without_sensitive_details():
    from pymysql.err import OperationalError
    from sqlalchemy.exc import OperationalError as DatabaseError
    error = DatabaseError("sensitive SQL", {"password": "secret"}, OperationalError(1049, "private database name"))
    message = module.error_message(error)
    assert "1049" in message
    assert "DB初期化" in message
    assert "secret" not in message
    assert "private database name" not in message
