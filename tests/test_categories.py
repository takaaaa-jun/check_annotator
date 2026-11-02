"""DB接続なしの入力検証と、SQLite上のトランザクション・制約検証。"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import IntegrityError

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("import_categories", ROOT / "scripts/import_categories.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@pytest.fixture
def data():
    path = ROOT / "data/categories/categories.json"
    if not path.exists():
        pytest.skip("Git対象外のdata/categories/categories.jsonを配置した場合のみ実データ検証")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def engine():
    engine = create_engine("sqlite://")
    @event.listens_for(engine, "connect")
    def enable_fks(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
    module.metadata.create_all(engine)
    yield engine
    engine.dispose()


def count(connection, table):
    return connection.scalar(select(func.count()).select_from(table))


def test_original_ids_and_partial_classification(data):
    assert module.validate(data) == dict(source_categories=256, food_categories=42, mappings=42, unmapped=214)
    names = {row["id"]: row["name"] for row in data["source_categories"]}
    assert names[19] == "sandwiches"
    assert names[20] == "udon noodle"
    assert names[21] == "tempura udon"
    assert names[40] == names[67] == "omelet"
    assert names[256] == "hot & sour soup"
    assert all(row["source_id"] != 38 for row in data["classifications"])


@pytest.mark.parametrize("change, message", [
    (lambda d: d["source_categories"].append(d["source_categories"][0]), "重複"),
    (lambda d: d["classifications"].append(d["classifications"][0]), "重複"),
    (lambda d: d["classifications"][0].update(source_id=999), "不明"),
    (lambda d: d["classifications"][0].update(target_level=6), "category6"),
    (lambda d: d["classifications"][0].update(target_level=4), "target_level"),
    (lambda d: d["classifications"][0].update(category5=""), "カテゴリ名"),
    (lambda d: d["classifications"][9].update(category5_description="競合"), "説明が競合"),
])
def test_bad_data_rejected(data, change, message):
    change(data)
    with pytest.raises(ValueError, match=message):
        module.validate(data)


def test_import_is_repeatable_and_deduplicates_masters(engine, data):
    with engine.begin() as connection:
        module.import_data(connection, data)
        before = {table.name: count(connection, table) for table in module.metadata.sorted_tables}
        module.import_data(connection, data)
        assert before == {table.name: count(connection, table) for table in module.metadata.sorted_tables}
        assert before["source_categories"] == 256
        assert before["category_replacement_mappings"] == 42
        assert connection.scalar(select(func.count()).select_from(module.masters[5]).where(
            module.masters[5].c.name == "ピラフ")) == 1
        assert connection.scalar(select(func.count()).select_from(module.masters[5]).where(
            module.masters[5].c.name == "サンドウィッチ")) == 1


def test_conflict_rolls_back_new_rows(engine, data):
    with engine.begin() as connection:
        module.import_data(connection, data)
    changed = deepcopy(data)
    changed["source_categories"].insert(0, {"id": 257, "name": "new"})
    changed["source_categories"][1]["name"] = "changed"
    with pytest.raises(ValueError, match="競合"):
        with engine.begin() as connection:
            module.import_data(connection, changed)
    with engine.connect() as connection:
        assert count(connection, module.source_categories) == 256


def test_null_category6_path_duplicate_rejected(engine, data):
    with engine.begin() as connection:
        module.import_data(connection, data)
        row = dict(connection.execute(select(module.food_categories).where(
            module.food_categories.c.category6_id.is_(None))).mappings().first())
        row.pop("food_category_id")
        row.pop("category6_key")
        row["code"] = "duplicate"
        with connection.begin_nested():
            with pytest.raises(IntegrityError):
                connection.execute(module.food_categories.insert().values(**row))


def test_invalid_fk_and_mapping_level_rejected(engine, data):
    with engine.begin() as connection:
        module.import_data(connection, data)
        row = dict(connection.execute(select(module.category_replacement_mappings)).mappings().first())
        row.pop("mapping_id")
        row.pop("active_source_key")
        for changes in ({"target_level": 7, "deleted_at": row["created_at"]},
                        {"source_category_id": 999999}, {}):
            with connection.begin_nested():
                with pytest.raises(IntegrityError):
                    connection.execute(module.category_replacement_mappings.insert().values(**(row | changes)))


def test_soft_deleted_mapping_can_be_replaced(engine, data):
    with engine.begin() as connection:
        module.import_data(connection, data)
        table = module.category_replacement_mappings
        row = connection.execute(select(table)).mappings().first()
        connection.execute(table.update().where(table.c.mapping_id == row["mapping_id"]).values(deleted_at=row["created_at"]))
        module.import_data(connection, data)
        assert count(connection, table) == 43


def test_generated_sql_matches_metadata():
    from sqlalchemy.dialects.mysql import dialect
    from sqlalchemy.schema import CreateTable
    sql = (ROOT / "sql/006_create_categories.sql").read_text(encoding="utf-8")
    for table in module.metadata.sorted_tables:
        statement = str(CreateTable(table).compile(dialect=dialect())).strip() + ";"
        assert "\n".join(line.rstrip() for line in statement.splitlines()) in sql


def test_transfer_checksum():
    import hashlib
    directory = ROOT / "data/categories"
    if not (directory / "categories.json.sha256").exists():
        pytest.skip("SCP用データ・チェックサムを配置した場合のみ検証")
    assert hashlib.sha256((directory / "categories.json").read_bytes()).hexdigest() == (
        directory / "categories.json.sha256").read_text().split()[0]


@pytest.mark.parametrize("code", [1044, 1045, 1142, 2003, 2026, 9999])
def test_db_error_does_not_expose_credentials_or_sql(code):
    from sqlalchemy.exc import OperationalError
    error = OperationalError("secret SQL", {"password": "private"},
                             Exception(code, "sensitive user/host/password details"))
    message = module.error_message(error)
    assert str(code) in message
    for secret in ("secret SQL", "private", "sensitive"):
        assert secret not in message


def test_check_db_rejects_write_options(monkeypatch):
    monkeypatch.setattr("sys.argv", ["import_categories.py", "--check-db", "--apply"])
    with pytest.raises(SystemExit) as error:
        module.main()
    assert error.value.code == 2
