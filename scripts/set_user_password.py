"""初期ユーザーのログイン用パスワードを非表示入力で設定する。"""
import argparse
from datetime import UTC, datetime
import getpass
from pathlib import Path
import sys
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def read_password(read_secret=getpass.getpass):
    # 非表示入力が使えない環境で平文入力にフォールバックしない。
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        password = read_secret("新しいログイン用パスワード（8文字以上）: ")
        confirmation = read_secret("確認のため再入力: ")
    if password != confirmation:
        raise RuntimeError("パスワードが一致しません。変更していません。")
    if len(password) < 8:
        raise RuntimeError("パスワードは8文字以上にしてください。変更していません。")
    return password


def set_initial_password(session, user_name, password):
    from sqlalchemy import select, update
    from app.core.security import password_hash
    from app.models.user import User
    # relationshipの参照先をモデルへ登録する。
    from app.models.role import Role  # noqa: F401

    user_id = session.scalar(select(User.user_id).where(
        User.user_name == user_name, User.deleted_at.is_(None),
        User.password_hash == "!",
    ))
    if user_id is None:
        raise RuntimeError("未設定の有効ユーザーが見つかりません。設定済みパスワードは上書きしません。")
    if len(password) < 8:
        raise RuntimeError("パスワードは8文字以上にしてください。")
    result = session.execute(update(User).where(
        User.user_id == user_id, User.deleted_at.is_(None), User.password_hash == "!",
    ).values(password_hash=password_hash.hash(password), updated_at=datetime.now(UTC).replace(tzinfo=None)))
    if result.rowcount != 1:
        session.rollback()
        raise RuntimeError("ユーザーが変更されたため停止しました。再確認してください。")
    session.commit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user_name", help="初期パスワードを設定するユーザー名")
    args = parser.parse_args()
    from sqlalchemy.engine import make_url
    from app.database import SessionLocal, database_url

    url = make_url(database_url)
    if url.drivername != "mysql+pymysql" or url.database != "check_annotator":
        raise RuntimeError("対象はMySQLのcheck_annotatorに限定しています。")
    print(f"対象: host={url.host}, port={url.port or 3306}, database={url.database}, user={args.user_name}")
    if input("対象DB名を再入力してください: ") != "check_annotator":
        raise RuntimeError("DB名が一致しません。変更していません。")
    password = read_password()
    with SessionLocal() as session:
        set_initial_password(session, args.user_name, password)
    print(f"{args.user_name} のログイン用パスワードを設定しました。")


def error_message(error):
    # DB例外の本文やSQLパラメーターを出さず、番号と対処だけを表示する。
    from sqlalchemy.exc import DBAPIError
    if isinstance(error, DBAPIError):
        code = error.orig.args[0] if error.orig.args else None
        messages = {
            1049: "対象DBがありません。先にcheck_annotatorのDB初期化を実行してください。",
            1045: "DB認証が拒否されました。DBユーザー・パスワード・接続元の許可を確認してください。",
            1146: "必要なテーブルがありません。DB初期化の適用状態を確認してください。",
            1142: "DB操作の権限がありません。usersのSELECT・UPDATE権限を確認してください。",
            2003: "MySQLへ接続できません。接続先・ポート・ネットワークを確認してください。",
            2013: "MySQLとの接続が切れました。接続状態を確認してください。",
        }
        if isinstance(code, int):
            return f"MySQLエラー {code}: {messages.get(code, 'DB接続設定と権限を確認してください。')}"
        return "DB接続または操作に失敗しました。接続設定と権限を確認してください。"
    return str(error) if isinstance(error, RuntimeError) else type(error).__name__


if __name__ == "__main__":
    try:
        main()
    except (Exception, KeyboardInterrupt) as error:
        # DB例外にはSQLのパラメーターが含まれ得るため出力しない。
        print(f"設定を停止しました: {error_message(error)}", file=sys.stderr)
        sys.exit(1)
