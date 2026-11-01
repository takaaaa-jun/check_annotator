"""担当表をバックアップし、グループの担当者だけを解除する。"""
import argparse
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import sys
import uuid

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))


def fingerprint(connection, table):
    from sqlalchemy import text
    key = {"tasks": "task_id", "comments": "comment_id"}[table]
    digest = hashlib.sha256()
    count = 0
    for row in connection.execute(text(f"SELECT * FROM `{table}` ORDER BY {key}")).mappings():
        digest.update(json.dumps(dict(row), default=str, sort_keys=True).encode("utf-8"))
        count += 1
    return {"count": count, "sha256": digest.hexdigest()}


def unassign(connection, backup_path, expected_count, target):
    from sqlalchemy import text
    lock = " FOR UPDATE" if connection.dialect.name == "mysql" else ""
    groups = [dict(row) for row in connection.execute(text(
        "SELECT group_id,group_name,user_id,updated_at FROM `groups` "
        "WHERE deleted_at IS NULL ORDER BY group_id" + lock)).mappings()]
    assigned = [row for row in groups if row["user_id"] is not None]
    if len(assigned) != expected_count:
        raise RuntimeError("割り当て件数が事前確認と異なります。変更していません。")
    preserved = {table: fingerprint(connection, table) for table in ("tasks", "comments")}
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    with backup_path.open("x", encoding="utf-8") as handle:
        json.dump({"created_at": datetime.now(UTC).isoformat(), "target": target,
                   "groups": groups, "preserved": preserved}, handle, ensure_ascii=False, indent=2, default=str)
        handle.flush()
        import os
        os.fsync(handle.fileno())
    now = datetime.now(UTC).replace(tzinfo=None)
    for group in assigned:
        result = connection.execute(text("UPDATE `groups` SET user_id=NULL, updated_at=:now "
            "WHERE group_id=:id AND user_id=:owner AND deleted_at IS NULL"),
            {"now": now, "id": group["group_id"], "owner": group["user_id"]})
        if result.rowcount != 1:
            raise RuntimeError("担当表が同時に変更されたため、処理を取り消します。")
    remaining = connection.execute(text("SELECT COUNT(*) FROM `groups` WHERE deleted_at IS NULL AND user_id IS NOT NULL")).scalar_one()
    if remaining or any(fingerprint(connection, table) != previous for table, previous in preserved.items()):
        raise RuntimeError("検証不一致のため、処理を取り消します。")
    return {"released_groups": len(assigned), "remaining_assigned": remaining, "preserved": preserved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=["server", "preview"], required=True)
    parser.add_argument("--expected-count", type=int, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path, default=Path(__file__).resolve().parents[1] / "backups")
    args = parser.parse_args()
    from sqlalchemy import text
    from app.database import engine
    import os
    if args.target == "server":
        if engine.url.drivername != "mysql+pymysql" or engine.url.host != "133.35.129.9" or engine.url.database != "check_annotator":
            raise RuntimeError("接続先が指定のサーバーDBと一致しません。")
    elif engine.dialect.name != "sqlite" or os.getenv("APP_DATA_MODE") != "mock" or not str(engine.url.database).endswith("admin-preview.db"):
        raise RuntimeError("接続先が専用のローカル仮データDBと一致しません。")
    with engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM `groups` WHERE deleted_at IS NULL AND user_id IS NOT NULL")).scalar_one()
    print(json.dumps({"target": args.target, "assigned_groups": count, "apply": args.apply}, ensure_ascii=False))
    if not args.apply:
        return
    path = args.backup_dir / ("assignments-" + args.target + "-" + uuid.uuid4().hex + ".json")
    with engine.begin() as connection:
        result = unassign(connection, path, args.expected_count, args.target)
    print(json.dumps(dict(result, backup=str(path)), ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
    except Exception as error:
        print(type(error).__name__ + ": 処理を停止しました。DBとバックアップを確認してください。", file=sys.stderr)
        sys.exit(1)
