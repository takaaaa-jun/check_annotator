"""隔離MySQLで実コマンドと配布DDLを検証する。

専用の空DBだけを指定する。CATEGORY_TEST_MYSQL_URL未設定時はスキップ。
例: mysql+pymysql://root@127.0.0.1:13316/check_annotator?charset=utf8mb4
通常の.envやDATABASE_URLは使わない。localhostの標準外ポートに限定する。
"""
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("mysql_import_categories", ROOT / "scripts/import_categories.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
BASE_TABLES = ("roles", "users", "groups", "states", "tasks", "comments")


def statements(path):
    sql = re.sub(r"(?m)^\s*--.*$", "", path.read_text(encoding="utf-8"))
    return [part.strip() for part in sql.split(";") if part.strip()]


@pytest.fixture
def mysql():
    configured = os.environ.get("CATEGORY_TEST_MYSQL_URL")
    if not configured:
        pytest.skip("CATEGORY_TEST_MYSQL_URLで隔離MySQLを指定した場合のみ実行")
    if not (ROOT / "data/categories/categories.json").exists():
        pytest.fail("実MySQL検証にはGit対象外のdata/categories/categories.jsonの配置が必要です。")
    url = make_url(configured)
    if (url.drivername != "mysql+pymysql" or url.host != "127.0.0.1"
            or url.port not in (13316, 13317) or url.database != "check_annotator"):
        pytest.fail("テスト接続先は127.0.0.1:13316/13317の専用check_annotator DBに限定")
    engine = create_engine(url)
    with engine.connect() as connection:
        if inspect(connection).get_table_names():
            engine.dispose()
            pytest.fail("専用の空DBが必要です。既存DBは変更しません。")
    try:
        # 実運用と同じ6テーブル・初期値を先に作り、カテゴリ投入で保持されるか確認する。
        with engine.connect() as connection:
            for filename in ("001_create_users.sql", "002_seed_users.sql", "003_create_groups_tasks.sql",
                             "004_create_comments.sql", "005_seed_states.sql"):
                for statement in statements(ROOT / "sql" / filename):
                    connection.exec_driver_sql(statement)
            connection.exec_driver_sql("INSERT INTO `groups` (group_name,user_id,created_at,updated_at) "
                                       "VALUES ('existing-group',1,UTC_TIMESTAMP(),UTC_TIMESTAMP())")
            connection.exec_driver_sql("INSERT INTO tasks (group_id,image_id,state_id,created_at,updated_at) "
                                       "VALUES (1,4001,1,UTC_TIMESTAMP(),UTC_TIMESTAMP())")
            connection.exec_driver_sql("INSERT INTO comments (task_id,user_id,content,created_at,updated_at) "
                                       "VALUES (1,1,'existing comment',UTC_TIMESTAMP(),UTC_TIMESTAMP())")
            connection.commit()
        yield engine, configured
    finally:
        # このfixtureが空の専用DBに作成した既知のテーブルだけを削除する。
        with engine.connect() as connection:
            for table in reversed(module.metadata.sorted_tables):
                table.drop(connection, checkfirst=True)
            for name in reversed(BASE_TABLES):
                connection.exec_driver_sql(f"DROP TABLE IF EXISTS `{name}`")
            connection.commit()
        engine.dispose()


def run_cli(url, *arguments):
    environment = os.environ | {"DATABASE_URL": url, "PYTHONIOENCODING": "utf-8", "APP_DATA_MODE": "database"}
    return subprocess.run([sys.executable, str(ROOT / "scripts/import_categories.py"), *arguments],
                          env=environment, capture_output=True, text=True, encoding="utf-8", timeout=60)


def snapshot(engine, tables):
    with engine.connect() as connection:
        # MySQLではロールバックしても採番済み番号は戻らない。行と構造を比較し、
        # SHOW CREATE TABLEの次回採番値だけは比較から除く。
        return {name: (re.sub(r" AUTO_INCREMENT=\d+", "", connection.exec_driver_sql(f"SHOW CREATE TABLE `{name}`").one()[1]),
                       connection.exec_driver_sql(f"SELECT * FROM `{name}` ORDER BY 1").all()) for name in tables}


@pytest.mark.parametrize("route", ["create-schema", "sql-file"])
def test_mysql_full_import_and_existing_data_preservation(mysql, tmp_path, route):
    engine, url = mysql
    base_before = snapshot(engine, BASE_TABLES)
    data = json.loads((ROOT / "data/categories/categories.json").read_text(encoding="utf-8"))
    if route == "sql-file":
        with engine.connect() as connection:
            for statement in statements(ROOT / "sql/006_create_categories.sql"):
                connection.exec_driver_sql(statement)
            connection.commit()
    result = run_cli(url, "--apply", *( ["--create-schema"] if route == "create-schema" else []))
    assert result.returncode == 0, result.stdout + result.stderr
    categories_before = snapshot(engine, module.metadata.tables)
    assert len(categories_before["source_categories"][1]) == 256
    assert len(categories_before["food_categories"][1]) == 41
    assert len(categories_before["category_replacement_mappings"][1]) == 41
    repeated = run_cli(url, "--apply")
    assert repeated.returncode == 0, repeated.stdout + repeated.stderr
    assert snapshot(engine, module.metadata.tables) == categories_before
    check = run_cli(url, "--check-db")
    assert check.returncode == 0 and "10/10" in check.stdout, check.stdout + check.stderr
    assert snapshot(engine, module.metadata.tables) == categories_before
    refusal = run_cli(url, "--apply", "--create-schema")
    assert refusal.returncode != 0 and "既にあります" in refusal.stderr
    assert snapshot(engine, module.metadata.tables) == categories_before
    # 先に追加した257を含め、後続の競合検出でデータ行が全て戻るか検証。
    conflicting = deepcopy(data)
    conflicting["source_categories"].insert(0, {"id": 257, "name": "new category"})
    conflicting["source_categories"][1]["name"] = "conflicting name"
    conflict_file = tmp_path / "conflict.json"
    conflict_file.write_text(json.dumps(conflicting, ensure_ascii=False), encoding="utf-8")
    conflict = run_cli(url, "--apply", "--data", str(conflict_file))
    assert conflict.returncode != 0 and "競合" in conflict.stderr
    assert snapshot(engine, module.metadata.tables) == categories_before
    assert snapshot(engine, BASE_TABLES) == base_before
    # 未対応の外部ID38の分類を後から追加できることも実コマンドで確認する。
    extended = deepcopy(data)
    added = deepcopy(data["classifications"][0])
    added.update(source_id=38, category2="主菜", category3="焼き物", category4="皿物",
                 category5="ソーセージ", category5_description="")
    extended["classifications"].append(added)
    extension_file = tmp_path / "extension.json"
    extension_file.write_text(json.dumps(extended, ensure_ascii=False), encoding="utf-8")
    extension = run_cli(url, "--apply", "--data", str(extension_file))
    assert extension.returncode == 0, extension.stdout + extension.stderr
    after = snapshot(engine, module.metadata.tables)
    assert len(after["source_categories"][1]) == 256
    assert len(after["food_categories"][1]) == len(after["category_replacement_mappings"][1]) == 42
    assert snapshot(engine, BASE_TABLES) == base_before


def test_mysql_database_constraints(mysql):
    engine, url = mysql
    result = run_cli(url, "--apply", "--create-schema")
    assert result.returncode == 0, result.stdout + result.stderr
    with engine.begin() as connection:
        food = module.food_categories
        row = dict(connection.execute(select(food).where(food.c.category6_id.is_(None))).mappings().first())
        row.pop("food_category_id")
        row.pop("category6_key")
        row["code"] = "duplicate-null-path"
        with connection.begin_nested():
            with pytest.raises(IntegrityError):
                connection.execute(food.insert().values(**row))
        row["category1_id"] = 999999
        with connection.begin_nested():
            with pytest.raises(IntegrityError):
                connection.execute(food.insert().values(**row))
        mapping = module.category_replacement_mappings
        row = dict(connection.execute(select(mapping)).mappings().first())
        row.pop("mapping_id")
        row.pop("active_source_key")
        with connection.begin_nested():
            with pytest.raises(IntegrityError):
                connection.execute(mapping.insert().values(**row))
        row.update(target_level=7, deleted_at=row["created_at"])
        with connection.begin_nested():
            with pytest.raises(DBAPIError) as error:
                connection.execute(mapping.insert().values(**row))
            assert error.value.orig.args[0] == 3819
        # 論理削除した旧対応は履歴として保持し、新しい有効対応を登録できる。
        first = connection.execute(select(mapping)).mappings().first()
        connection.execute(mapping.update().where(mapping.c.mapping_id == first["mapping_id"]).values(
            deleted_at=first["created_at"]))
        module.import_data(connection, json.loads((ROOT / "data/categories/categories.json").read_text(encoding="utf-8")))
        assert connection.execute(text("SELECT COUNT(*) FROM category_replacement_mappings")).scalar_one() == 42


def test_mysql_lock_prevents_concurrent_import(mysql):
    engine, url = mysql
    with engine.connect() as connection:
        assert connection.execute(text("SELECT GET_LOCK('check_annotator.categories', 0)")).scalar_one() == 1
        try:
            blocked = run_cli(url, "--apply", "--create-schema")
            assert blocked.returncode != 0 and "別のカテゴリ投入処理" in blocked.stderr
            assert not (set(inspect(connection).get_table_names()) & set(module.metadata.tables))
        finally:
            connection.execute(text("SELECT RELEASE_LOCK('check_annotator.categories')"))
            connection.commit()
    success = run_cli(url, "--apply", "--create-schema")
    assert success.returncode == 0, success.stdout + success.stderr
    # コマンド終了後は他接続からロックを取得できる。
    with engine.connect() as connection:
        assert connection.execute(text("SELECT GET_LOCK('check_annotator.categories', 0)")).scalar_one() == 1
        connection.execute(text("SELECT RELEASE_LOCK('check_annotator.categories')"))
        connection.commit()
