"""転送用JSONの生成・検証・カテゴリ専用テーブルへの追加投入。"""
import argparse
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.db.category_schema import (  # noqa: E402
    metadata, masters, food_categories, category_sources,
    source_categories, category_replacement_mappings,
)
from sqlalchemy import inspect, select  # noqa: E402
from sqlalchemy.schema import CreateTable  # noqa: E402
from sqlalchemy.dialects.mysql import dialect  # noqa: E402


def error_message(error):
    """接続文字列・ユーザー名・SQL本文を表示せず原因を伝える。"""
    from sqlalchemy.exc import DBAPIError
    if isinstance(error, DBAPIError):
        arguments = getattr(error.orig, "args", ())
        code = arguments[0] if arguments and type(arguments[0]) is int else None
        hints = {
            1044: "対象DBへのアクセス権限を確認してください。",
            1045: "DB認証に失敗しました。ユーザー・パスワード・接続元の許可を確認してください。",
            1049: "対象DBがありません。DB名を確認してください。",
            1142: "実行した操作の権限が不足しています。DDL作成・参照・登録権限を確認してください。",
            1143: "カラムへの操作権限が不足しています。",
            1215: "外部キーを作成できません。参照先・型・既存テーブル定義を確認してください。",
            1822: "外部キーの参照先インデックスが不足しています。",
            2003: "MySQLに接続できません。接続先・ポート・ネットワーク・接続許可を確認してください。",
            2005: "DBホスト名を解決できません。接続先を確認してください。",
            2006: "MySQLとの接続が切断されました。",
            2013: "処理中にMySQLとの接続が失われました。",
            2026: "TLS接続に失敗しました。CA証明書と接続設定を確認してください。",
        }
        label = f"MySQLエラー {code}" if code is not None else type(error).__name__
        return label + ": " + hints.get(code, "DB設定・権限・サーバーログを確認してください。")
    return str(error) if isinstance(error, (ValueError, FileNotFoundError)) else type(error).__name__


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def category_code(level, name):
    return f"c{level}-" + digest(name)[:24]


def validate(data):
    if data.get("format_version") != 1:
        raise ValueError("対応していないformat_versionです。")
    source = data["source"]
    for key, limit in (("code", 100), ("name", 100), ("version", 50)):
        if not isinstance(source[key], str) or not source[key].strip() or len(source[key]) > limit:
            raise ValueError(f"source.{key}が不正です。")
    source_ids = set()
    for row in data["source_categories"]:
        if type(row["id"]) is not int or not 0 < row["id"] <= 4294967295 or row["id"] in source_ids:
            raise ValueError("元カテゴリIDが不正または重複しています。")
        if not isinstance(row["name"], str) or not row["name"].strip() or len(row["name"]) > 100:
            raise ValueError("元カテゴリ名が不正です。")
        source_ids.add(row["id"])
    if not source_ids:
        raise ValueError("元カテゴリが空です。")
    mapped, paths, descriptions = set(), set(), {}
    required = {"source_id", "target_level", *[f"category{i}" for i in range(1, 7)],
                "category5_description", "category6_description"}
    for row in data["classifications"]:
        if set(row) != required:
            raise ValueError("分類行の列が一致しません。")
        sid, level = row["source_id"], row["target_level"]
        if type(sid) is not int or sid not in source_ids or sid in mapped:
            raise ValueError("対応表に不明または重複した元カテゴリIDがあります。")
        if type(level) is not int or level not in (5, 6):
            raise ValueError("target_levelは5または6です。")
        names = []
        for i in range(1, 7):
            name = row[f"category{i}"]
            if not isinstance(name, str) or name != name.strip() or len(name) > 100 or (i <= 5 and not name):
                raise ValueError("カテゴリ名が空・長すぎるか、前後に空白があります。")
            names.append(name)
            description = row.get(f"category{i}_description", "")
            if not isinstance(description, str) or len(description.encode("utf-8")) > 65535:
                raise ValueError("説明文が不正です。")
            if description:
                key = (i, name)
                if key in descriptions and descriptions[key] != description:
                    raise ValueError("同一カテゴリの説明が競合しています。")
                descriptions[key] = description
        if level == 6 and not names[5]:
            raise ValueError("階層6への対応にcategory6がありません。")
        if not names[5] and row["category6_description"]:
            raise ValueError("category6なしで説明だけ指定されています。")
        paths.add(tuple(names))
        mapped.add(sid)
    return {"source_categories": len(source_ids), "food_categories": len(paths),
            "mappings": len(mapped), "unmapped": len(source_ids - mapped)}


def build_bundle():
    directory = ROOT / "data/categories"
    names = (directory / "source_names.txt").read_text(encoding="utf-8").splitlines()
    if len(names) != 256:
        raise ValueError("初期の元カテゴリは256件必要です。")
    with (directory / "classifications.tsv").open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter="\t"))
    for row in rows:
        row["source_id"] = int(row["source_id"])
        row["target_level"] = int(row["target_level"])
    data = {"format_version": 1,
            "source": {"code": "original-food-256-v1", "name": "元料理カテゴリ256種類", "version": "1"},
            "source_categories": [{"id": i, "name": name} for i, name in enumerate(names, 1)],
            "classifications": rows}
    validate(data)
    output = directory / "categories.json"
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    (directory / "categories.json.sha256").write_text(
        hashlib.sha256(output.read_bytes()).hexdigest() + "  categories.json\n", encoding="ascii", newline="\n")
    sql = "-- MySQL 8.0.16以上。既存6テーブルを変更しない追加DDL。\n"
    sql += "-- scripts/import_categories.py --build-bundle で生成。USEは接続先で指定。\n\n"
    sql += ";\n\n".join(str(CreateTable(table).compile(dialect=dialect())).strip()
                           for table in metadata.sorted_tables) + ";\n"
    sql = "\n".join(line.rstrip() for line in sql.splitlines()) + "\n"
    (ROOT / "sql/006_create_categories.sql").write_text(sql, encoding="utf-8", newline="\n")
    return output


def insert_or_match(connection, table, keys, values, now):
    row = connection.execute(select(table).filter_by(**keys)).mappings().one_or_none()
    if row:
        if row["deleted_at"] is not None or any(row[key] != value for key, value in values.items()):
            raise ValueError(f"既存データと競合: {table.name}。上書きせず停止します。")
        return row[next(iter(table.primary_key.columns)).name]
    result = connection.execute(table.insert().values(**keys, **values, created_at=now, updated_at=now))
    return result.inserted_primary_key[0]


def import_data(connection, data):
    """呼び出し元の単一トランザクション内で実行。既存行は一致確認のみ。"""
    validate(data)
    now = datetime.now(UTC).replace(tzinfo=None)
    source = data["source"]
    source_id = insert_or_match(connection, category_sources, {"code": source["code"]},
                                {"name": source["name"], "version": source["version"]}, now)
    source_keys = {}
    for row in data["source_categories"]:
        source_keys[row["id"]] = insert_or_match(connection, source_categories,
            {"category_source_id": source_id, "external_category_id": row["id"]}, {"name": row["name"]}, now)
    descriptions = {(i, row[f"category{i}"]): row[f"category{i}_description"]
                    for row in data["classifications"] for i in (5, 6)
                    if row[f"category{i}_description"]}
    for row in data["classifications"]:
        ids, codes = {}, []
        for i in range(1, 7):
            name = row[f"category{i}"]
            code = category_code(i, name) if name else ""
            codes.append(code)
            ids[f"category{i}_id"] = insert_or_match(connection, masters[i], {"code": code},
                {"name": name, "description": descriptions.get((i, name)), "sort_order": 0}, now) if name else None
        food_id = insert_or_match(connection, food_categories,
            {"code": "food-" + digest("/".join(codes))[:24]}, ids, now)
        # 有効な対応だけ比較。論理削除した旧対応は履歴として保持する。
        insert_or_match(connection, category_replacement_mappings,
            {"source_category_id": source_keys[row["source_id"]], "deleted_at": None},
            {"food_category_id": food_id, "target_level": row["target_level"]}, now)


def verify_schema(connection):
    import re
    inspector = inspect(connection)
    for table in metadata.sorted_tables:
        actual = {c["name"]: c for c in inspector.get_columns(table.name)}
        if set(actual) != set(table.columns.keys()):
            raise ValueError(f"スキーマの列が一致しません: {table.name}")
        for column in table.columns:
            found = actual[column.name]
            # MySQL反映型には文字列列のCHARACTER SET/COLLATEが付く。
            # 文字コード・照合順序は下のテーブルオプションで別途検証する。
            def normalized_type(type_):
                return re.split(r"\s+(?:CHARACTER SET|COLLATE)\s+",
                                type_.compile(dialect=dialect()).upper(), maxsplit=1)[0].replace("INTEGER", "INT")
            expected_type = normalized_type(column.type)
            found_type = normalized_type(found["type"])
            if expected_type != found_type or (not column.computed and found["nullable"] != column.nullable):
                raise ValueError(f"スキーマの型・NULL制約が一致しません: {table.name}.{column.name}")
            if column.computed:
                normalize = lambda s: "".join(c for c in s.lower() if c.isalnum() or c == "_")
                computed = found.get("computed", {})
                if normalize(computed.get("sqltext", "")) != normalize(str(column.computed.sqltext)) or not computed.get("persisted"):
                    raise ValueError(f"生成列が一致しません: {table.name}.{column.name}")
        if inspector.get_pk_constraint(table.name)["constrained_columns"] != [c.name for c in table.primary_key]:
            raise ValueError(f"主キーが一致しません: {table.name}")
        actual_unique = {tuple(c["column_names"]) for c in inspector.get_unique_constraints(table.name)}
        from sqlalchemy import UniqueConstraint
        expected_unique = {tuple(c.name for c in item.columns) for item in table.constraints if isinstance(item, UniqueConstraint)}
        if not expected_unique <= actual_unique:
            raise ValueError(f"一意制約が不足しています: {table.name}")
        fks = inspector.get_foreign_keys(table.name)
        for foreign_key in table.foreign_keys:
            if not any(fk["constrained_columns"] == [foreign_key.parent.name]
                       and fk["referred_table"] == foreign_key.column.table.name
                       and fk["referred_columns"] == [foreign_key.column.name]
                       and fk["options"].get("ondelete", "RESTRICT") == "RESTRICT"
                       and fk["options"].get("onupdate", "RESTRICT") == "RESTRICT" for fk in fks):
                raise ValueError(f"外部キーが不足しています: {table.name}")
        settings = inspector.get_table_options(table.name)
        if settings.get("mysql_engine") != "InnoDB" or settings.get("mysql_collate") != "utf8mb4_unicode_ci":
            raise ValueError(f"エンジン・照合順序が一致しません: {table.name}")
    checks = inspector.get_check_constraints("category_replacement_mappings")
    if not any(c["name"] == "ck_mapping_target_level" for c in checks):
        raise ValueError("対応先階層のCHECK制約がありません。")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-bundle", action="store_true", help="元資料から転送用JSONとDDLを生成（DB接続なし）")
    parser.add_argument("--data", type=Path, default=ROOT / "data/categories/categories.json")
    parser.add_argument("--apply", action="store_true", help="データをDBに登録する")
    parser.add_argument("--create-schema", action="store_true", help="カテゴリ専用テーブルが全て未作成の場合のみ作成")
    parser.add_argument("--check-db", action="store_true", help="DB接続・バージョン・既存カテゴリテーブルを参照のみで確認")
    args = parser.parse_args()
    if args.check_db and (args.apply or args.create_schema or args.build_bundle):
        parser.error("--check-dbは他の実行オプションと併用できません。")
    if args.build_bundle:
        if args.apply or args.create_schema:
            parser.error("--build-bundleはDB更新オプションと併用できません。")
        args.data = build_bundle()
    data = json.loads(args.data.read_text(encoding="utf-8"))
    print(json.dumps(validate(data), ensure_ascii=False))
    if not args.apply and not args.check_db:
        if args.create_schema:
            parser.error("--create-schemaには--applyが必要です。")
        print("検証のみ完了。DB接続・変更は行っていません。")
        return
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import make_url
    from app.database import build_database_url, build_engine_options
    url = make_url(build_database_url())
    if url.drivername != "mysql+pymysql" or url.database != "check_annotator":
        raise ValueError("接続先はmysql+pymysql / check_annotatorに限定しています。")
    print(f"対象: host={url.host}, port={url.port or 3306}, database={url.database}")
    engine = create_engine(url, **build_engine_options(str(url)))
    try:
        print("確認中: DB接続", flush=True)
        with engine.connect() as connection:
            print("確認中: MySQLバージョン", flush=True)
            version = connection.exec_driver_sql("SELECT VERSION()").scalar_one()
            import re
            match = re.match(r"(\d+)\.(\d+)\.(\d+)", version)
            if "mariadb" in version.lower() or not match or tuple(map(int, match.groups())) < (8, 0, 16):
                raise ValueError("MySQL 8.0.16以上が必要です。")
            if args.check_db:
                existing = set(inspect(connection).get_table_names()) & set(metadata.tables)
                print(f"接続成功。カテゴリテーブル: {len(existing)}/10")
                print("作成済み: " + (", ".join(sorted(existing)) or "なし"))
                print("未作成: " + (", ".join(sorted(set(metadata.tables) - existing)) or "なし"))
                print("参照のみ完了。テーブル作成・データ更新は行っていません。")
                return
            print("確認中: 投入ロック・既存テーブル", flush=True)
            if connection.execute(text("SELECT GET_LOCK('check_annotator.categories', 0)")).scalar() != 1:
                raise ValueError("別のカテゴリ投入処理が実行中です。")
            try:
                existing = set(inspect(connection).get_table_names()) & set(metadata.tables)
                if args.create_schema:
                    if existing:
                        raise ValueError("カテゴリテーブルが既にあります。--create-schemaを外して再実行してください。")
                    print("実行中: カテゴリ10テーブルの作成", flush=True)
                    metadata.create_all(connection, checkfirst=False)
                    connection.commit()
                elif existing != set(metadata.tables):
                    raise ValueError("カテゴリテーブルが不足しています。初回は--create-schemaを指定してください。")
                print("確認中: カテゴリテーブル定義", flush=True)
                verify_schema(connection)
                connection.commit()
                print("実行中: カテゴリデータ登録", flush=True)
                with connection.begin():
                    import_data(connection, data)
                print("登録完了。既存の一致行は維持し、新規行のみ追加しました。")
            finally:
                pending_error = sys.exc_info()[0] is not None
                try:
                    connection.rollback()
                    connection.execute(text("SELECT RELEASE_LOCK('check_annotator.categories')"))
                    connection.commit()
                except Exception:
                    if not pending_error:
                        raise
                    print("接続終了処理にも失敗しました。元のエラーを表示します。", file=sys.stderr)
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # DB例外に含まれる接続情報・投入値は表示しない。
        print(error_message(error), file=sys.stderr)
        sys.exit(1)
