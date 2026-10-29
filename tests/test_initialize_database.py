"""DB接続前の安全確認。pytest tests/test_initialize_database.py で実行。"""
import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("initialize_database", ROOT / "scripts/initialize_database.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def environment():
    return {"DB_INIT_PASSWORD_SHA256": hashlib.sha256(b"test-only").hexdigest()}


def test_confirmation_accepts_matching_secret_and_database():
    module.confirm_initialization(environment(), lambda _: "test-only", lambda _: "check_annotator")


def test_wrong_password_stops_before_database_confirmation():
    def unexpected(_):
        pytest.fail("パスワード不一致時にDB名確認へ進んではいけない")
    with pytest.raises(RuntimeError, match="パスワードが一致"):
        module.confirm_initialization(environment(), lambda _: "wrong", unexpected)


def test_wrong_database_stops():
    with pytest.raises(RuntimeError, match="DB名が一致"):
        module.confirm_initialization(environment(), lambda _: "test-only", lambda _: "other_database")


def test_missing_expected_secret_stops_before_input():
    with pytest.raises(RuntimeError, match="SHA-256"):
        module.confirm_initialization({}, lambda _: pytest.fail("入力不要"))


def test_environment_secret_does_not_prompt_for_password():
    env = environment() | {"DB_INIT_PASSWORD": "test-only"}
    module.confirm_initialization(env, lambda _: pytest.fail("秘密入力不要"), lambda _: "check_annotator")


@pytest.fixture
def fake_database(monkeypatch):
    # 実DBへ接続せず、既存DB保護とDDL失敗時の補償処理を確認する。
    import sys
    import types
    from unittest.mock import MagicMock
    import sqlalchemy

    database = types.ModuleType("app.database")
    database.build_database_url = lambda: "mysql+pymysql://test:secret@localhost/check_annotator"
    database.build_engine_options = lambda _: {}
    monkeypatch.setitem(sys.modules, "app.database", database)
    connection = MagicMock()
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value = connection
    def create_engine(url, **kwargs):
        connection.initial_url = url
        return engine
    monkeypatch.setattr(sqlalchemy, "create_engine", create_engine)
    monkeypatch.setattr(module, "confirm_initialization", lambda _: None)
    monkeypatch.setattr(module, "verify_schema", lambda _: None)
    monkeypatch.setattr(module, "verify_foreign_keys", lambda _: None)
    monkeypatch.setattr(module, "verify_api", lambda: None)
    monkeypatch.setenv("APP_DATA_MODE", "database")
    return connection


def configure_fake(connection, *, existing=False, tables=0, fail_on=None):
    from unittest.mock import MagicMock
    def execute(query):
        if fail_on and fail_on in query:
            raise ValueError("simulated failure")
        result = MagicMock()
        if "GET_LOCK" in query:
            result.scalar.return_value = 1
        elif "SELECT SCHEMA_NAME" in query:
            result.scalar.return_value = "check_annotator" if existing else None
        elif "SELECT COUNT(*)" in query:
            result.scalar.return_value = tables
        elif "DEFAULT_COLLATION_NAME" in query:
            result.scalar.return_value = "utf8mb4_unicode_ci"
        return result
    connection.exec_driver_sql.side_effect = execute


def executed(connection):
    return [call.args[0] for call in connection.exec_driver_sql.call_args_list]


def test_existing_tables_are_never_modified(fake_database):
    configure_fake(fake_database, existing=True, tables=6)
    with pytest.raises(RuntimeError, match="既存テーブル"):
        module.initialize()
    assert not any(query.startswith(("CREATE", "DROP", "INSERT", "UPDATE", "DELETE"))
                   for query in executed(fake_database))


def test_confirmation_failure_does_not_connect_or_modify_database(fake_database, monkeypatch):
    def reject(_):
        raise RuntimeError("パスワードが一致しません。")
    monkeypatch.setattr(module, "confirm_initialization", reject)
    with pytest.raises(RuntimeError, match="パスワード"):
        module.initialize()
    fake_database.exec_driver_sql.assert_not_called()


def test_partial_failure_drops_only_new_tables_in_reverse_order(fake_database):
    configure_fake(fake_database, existing=True, fail_on="CREATE TABLE states")
    with pytest.raises(ValueError):
        module.initialize()
    drops = [query for query in executed(fake_database) if query.startswith("DROP")]
    assert drops == ["DROP TABLE `groups`", "DROP TABLE `users`", "DROP TABLE `roles`"]


def test_failed_new_database_is_removed(fake_database):
    configure_fake(fake_database, fail_on="CREATE TABLE roles")
    with pytest.raises(ValueError):
        module.initialize()
    assert fake_database.initial_url.database == ""
    assert "DROP DATABASE check_annotator" in executed(fake_database)


def test_verification_failure_cleans_up_all_new_tables(fake_database, monkeypatch):
    configure_fake(fake_database, existing=True)
    def fail(_):
        raise RuntimeError("schema verification failed")
    monkeypatch.setattr(module, "verify_schema", fail)
    with pytest.raises(RuntimeError, match="schema verification"):
        module.initialize()
    assert [query for query in executed(fake_database) if query.startswith("DROP")] == [
        f"DROP TABLE `{name}`" for name in reversed(module.TABLES)
    ]
