"""MySQL専用の初期化。実行方法は docs/DB初期化.md を参照。"""
import getpass
import hashlib
import hmac
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

TABLES = ("roles", "users", "groups", "states", "tasks", "comments")
FILES = (
    "001_create_users.sql", "002_seed_users.sql",
    "003_create_groups_tasks.sql", "004_create_comments.sql", "005_seed_states.sql",
)


def confirm_initialization(environment, read_secret=getpass.getpass, read_text=input):
    expected = environment.get("DB_INIT_PASSWORD_SHA256", "")
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise RuntimeError("DB_INIT_PASSWORD_SHA256 に初期化専用パスワードのSHA-256を設定してください。")
    supplied = environment.get("DB_INIT_PASSWORD") or read_secret("初期化専用パスワード: ")
    actual = hashlib.sha256(supplied.encode("utf-8")).hexdigest()
    if not hmac.compare_digest(actual, expected.lower()):
        raise RuntimeError("初期化専用パスワードが一致しません。")
    if read_text("対象DB名を再入力してください: ") != "check_annotator":
        raise RuntimeError("DB名が一致しません。")


def statements(path):
    # このリポジトリのSQLのみ対象。文字列内のセミコロン等を使うSQLは追加しない。
    source = re.sub(r"(?m)^\s*--.*$", "", path.read_text(encoding="utf-8"))
    return [part.strip() for part in source.split(";") if part.strip()]


def verify_schema(connection):
    from sqlalchemy import inspect
    from sqlalchemy.dialects.mysql import dialect
    from app.db.base import Base
    from app.models import role, user, group, state, task, comment  # noqa: F401

    inspector = inspect(connection)
    if set(inspector.get_table_names(schema="check_annotator")) != set(TABLES):
        raise RuntimeError("テーブル一覧が一致しません。")
    for name in TABLES:
        model = Base.metadata.tables[name]
        columns = {column["name"]: column for column in inspector.get_columns(name, schema="check_annotator")}
        if set(columns) != set(model.columns.keys()):
            raise RuntimeError(f"{name}: カラム一覧が一致しません。")
        for column in model.columns:
            actual = columns[column.name]
            expected_type = column.type.compile(dialect=dialect()).upper()
            actual_type = actual["type"].compile(dialect=dialect()).upper()
            # MySQLの反映型に付く文字コード・照合順序はテーブル単位で別途確認する。
            actual_type = re.split(r"\s+(?:CHARACTER SET|COLLATE)\s+", actual_type, maxsplit=1)[0]
            # MySQLバージョンによるINTEGER/INT表記差を正規化。
            if actual_type.replace("INTEGER", "INT") != expected_type.replace("INTEGER", "INT"):
                raise RuntimeError(f"{name}.{column.name}: 型が一致しません。")
            if actual["nullable"] != column.nullable:
                raise RuntimeError(f"{name}.{column.name}: NULL制約が一致しません。")
            if column.primary_key and not actual.get("autoincrement"):
                raise RuntimeError(f"{name}: AUTO_INCREMENTがありません。")
        if inspector.get_pk_constraint(name, schema="check_annotator")["constrained_columns"] != [c.name for c in model.primary_key]:
            raise RuntimeError(f"{name}: 主キーが一致しません。")
        for constraint in model.constraints:
            from sqlalchemy import UniqueConstraint
            if isinstance(constraint, UniqueConstraint):
                if tuple(c.name for c in constraint.columns) not in {
                    tuple(item["column_names"]) for item in inspector.get_unique_constraints(name, schema="check_annotator")
                }:
                    raise RuntimeError(f"{name}: UNIQUE制約がありません。")
        foreign_keys = inspector.get_foreign_keys(name, schema="check_annotator")
        if len(foreign_keys) != len(model.foreign_key_constraints):
            raise RuntimeError(f"{name}: 外部キー数が一致しません。")
        for expected in model.foreign_key_constraints:
            element = next(iter(expected.elements))
            matches = [fk for fk in foreign_keys if fk["constrained_columns"] == [element.parent.name]]
            if len(matches) != 1:
                raise RuntimeError(f"{name}: 外部キーがありません。")
            actual = matches[0]
            if (actual["referred_table"] != element.column.table.name
                    or actual["referred_columns"] != [element.column.name]
                    or actual["options"].get("onupdate", "RESTRICT") != expected.onupdate
                    or actual["options"].get("ondelete", "RESTRICT") != expected.ondelete):
                raise RuntimeError(f"{name}: 外部キー定義が一致しません。")
        options = inspector.get_table_options(name, schema="check_annotator")
        if options.get("mysql_engine") != "InnoDB" or options.get("mysql_collate") != "utf8mb4_unicode_ci":
            raise RuntimeError(f"{name}: エンジンまたは照合順序が一致しません。")

    indexes = {
        "groups": [("user_id",)],
        "tasks": [("group_id",), ("state_id",), ("group_id", "state_id")],
        "comments": [("task_id",), ("user_id",), ("parent_id",), ("task_id", "created_at")],
    }
    for name, required in indexes.items():
        actual = {tuple(index["column_names"]) for index in inspector.get_indexes(name, schema="check_annotator")}
        if not set(required) <= actual:
            raise RuntimeError(f"{name}: 検索インデックスが不足しています。")
    states = connection.exec_driver_sql("SELECT state_id, state_name FROM states ORDER BY state_id").all()
    if states != [(1, "未着手"), (2, "完了"), (3, "付与予定ラベル"), (4, "コメント")]:
        raise RuntimeError("状態マスターが一致しません。")
    roles = dict(connection.exec_driver_sql("SELECT role_name, COUNT(*) FROM roles GROUP BY role_name").all())
    if roles != {"admin": 1, "worker": 1}:
        raise RuntimeError("ロールマスターが一致しません。")
    users = dict(connection.exec_driver_sql(
        "SELECT u.user_name, r.role_name FROM users u JOIN roles r ON r.role_id=u.role_id"
    ).all())
    expected_users = {name: "worker" for name in ("kimura", "imai", "umehara", "endo", "sato", "tabe", "matunaga")}
    expected_users["takahashi"] = "admin"
    if users != expected_users:
        raise RuntimeError("初期ユーザーが一致しません。")


def verify_api():
    # 外部HTTP URLへ認証情報を送らず、アプリと同じDB設定で既存APIを実行する。
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from app.core.security import create_access_token
    from app.database import engine
    from app.main import app
    with TestClient(app) as client:
        response = client.get("/health/database")
        if response.status_code != 200 or response.json().get("database") != "connected":
            raise RuntimeError("DBヘルスチェックに失敗しました。")
        response = client.post("/api/auth/login", json={"user_name": "takahashi", "password": "invalid"})
        if response.status_code != 401:
            raise RuntimeError("既存ログインAPIの確認に失敗しました。")
        if client.get("/api/users/me").status_code != 401:
            raise RuntimeError("既存ユーザーAPIの確認に失敗しました。")
        with engine.connect() as connection:
            user_id = connection.execute(text(
                "SELECT user_id FROM users WHERE user_name='takahashi' AND deleted_at IS NULL"
            )).scalar_one()
        # 初期パスワードを有効化せず、メモリ上の短期トークンで認証済みAPIを確認。
        client.cookies.set("access_token", create_access_token(user_id))
        response = client.get("/api/users/me")
        if (response.status_code != 200
                or response.json().get("user_name") != "takahashi"
                or response.json().get("role_name") != "admin"):
            raise RuntimeError("認証済みユーザーAPIの確認に失敗しました。")
        response = client.get(f"/api/users/{user_id}/groups")
        if response.status_code != 200:
            raise RuntimeError("グループAPIの確認に失敗しました。")


def verify_foreign_keys(connection):
    from sqlalchemy.exc import IntegrityError
    probes = (
        "INSERT INTO `groups` (group_name, user_id, created_at, updated_at) "
        "VALUES ('__fk_probe__', 4294967295, UTC_TIMESTAMP(), UTC_TIMESTAMP())",
        "INSERT INTO tasks (image_id, state_id, created_at, updated_at) "
        "VALUES (1, 4294967295, UTC_TIMESTAMP(), UTC_TIMESTAMP())",
        "INSERT INTO comments (task_id, user_id, content, created_at, updated_at) "
        "VALUES (4294967295, 4294967295, 'probe', UTC_TIMESTAMP(), UTC_TIMESTAMP())",
    )
    for query in probes:
        savepoint = connection.begin_nested()
        try:
            connection.exec_driver_sql(query)
        except IntegrityError as error:
            if error.orig.args[0] != 1452:
                raise RuntimeError("外部キー検証が想定外の制約で失敗しました。") from None
        else:
            raise RuntimeError("外部キーに反するデータを登録できてしまいました。")
        finally:
            savepoint.rollback()


def initialize():
    from sqlalchemy import create_engine
    from sqlalchemy.engine import make_url
    from app.database import build_database_url, build_engine_options

    url = make_url(build_database_url())
    if url.drivername != "mysql+pymysql" or url.database != "check_annotator":
        raise RuntimeError("接続先は mysql+pymysql / check_annotator に限定しています。")
    if os.environ.get("APP_DATA_MODE", "database") != "database":
        raise RuntimeError("APP_DATA_MODE=database で実行してください。")
    print(f"対象: host={url.host}, port={url.port or 3306}, database={url.database}")
    confirm_initialization(os.environ)
    # 全ファイルをDB変更前に読み込む。
    commands = [command for name in FILES for command in statements(ROOT / "sql" / name)]
    # URL.set(database=None) は既存値を保持するため、空文字でDB指定を外す。
    admin_engine = create_engine(url.set(database=""), **build_engine_options(str(url)))
    created_database = False
    created_tables = []
    with admin_engine.connect() as connection:
        if connection.exec_driver_sql("SELECT GET_LOCK('check_annotator.initialize', 0)").scalar() != 1:
            raise RuntimeError("別の初期化が実行中です。")
        try:
            existing = connection.exec_driver_sql(
                "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='check_annotator'"
            ).scalar()
            if existing:
                count = connection.exec_driver_sql(
                    "SELECT COUNT(*) FROM information_schema.TABLES WHERE TABLE_SCHEMA='check_annotator'"
                ).scalar()
                if count:
                    raise RuntimeError("既存テーブルがあります。削除・上書きせず停止します。")
                collation = connection.exec_driver_sql(
                    "SELECT DEFAULT_COLLATION_NAME FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='check_annotator'"
                ).scalar()
                if collation != "utf8mb4_unicode_ci":
                    raise RuntimeError("既存の空DBの照合順序を utf8mb4_unicode_ci に揃えてください。")
            else:
                connection.exec_driver_sql(
                    "CREATE DATABASE check_annotator CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
                created_database = True
            connection.exec_driver_sql("USE check_annotator")
            connection.exec_driver_sql("SET time_zone = '+00:00'")
            for command in commands:
                connection.exec_driver_sql(command)
                match = re.match(r"CREATE TABLE `?(\w+)`?", command, re.I)
                if match:
                    created_tables.append(match.group(1))
            connection.commit()
            verify_schema(connection)
            verify_foreign_keys(connection)
            connection.rollback()
            verify_api()
            print("完了: 6テーブル・制約・インデックス・初期データ・DBヘルスチェック・既存APIを確認しました。")
        except BaseException:
            # MySQL DDLは暗黙コミット。今回作成したものだけ逆順で補償削除する。
            try:
                connection.rollback()
                for name in reversed(created_tables):
                    connection.exec_driver_sql(f"DROP TABLE `{name}`")
                if created_database:
                    connection.exec_driver_sql("DROP DATABASE check_annotator")
                connection.commit()
            except Exception:
                print("復旧処理に失敗しました。DBの状態を管理者が確認してください。", file=sys.stderr)
            raise
        finally:
            try:
                connection.exec_driver_sql("SELECT RELEASE_LOCK('check_annotator.initialize')")
            except Exception:
                # 接続断の場合はMySQLがセッション終了時にロックを解放する。
                print("接続が失われました。DBと初期化ロックの状態を管理者が確認してください。", file=sys.stderr)
    admin_engine.dispose()


if __name__ == "__main__":
    try:
        initialize()
    except (Exception, KeyboardInterrupt) as error:
        # ドライバー例外には接続情報やSQLが含まれ得るため、そのまま表示しない。
        message = str(error) if isinstance(error, RuntimeError) else type(error).__name__
        print(f"初期化を停止しました: {message}", file=sys.stderr)
        sys.exit(1)
