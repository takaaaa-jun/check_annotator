"""指定された画像範囲をグループとして担当者へ初回割当する。"""
import argparse
from datetime import UTC, datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

ASSIGNMENTS = {
    2: [(1, 1000), (7001, 8000), (14001, 15000), (21001, 22000),
        (23001, 24000), (25001, 26000), (26001, 27000), (29001, 29700)],
    3: [(1001, 2000), (8001, 9000), (15001, 16000), (22001, 23000),
        (24001, 25000), (29701, 30000)],
    4: [(2001, 3000), (9001, 10000), (16001, 17000), (27001, 27400)],
    5: [(3001, 4000), (10001, 11000), (17001, 18000), (27401, 27800)],
    6: [(4001, 5000), (11001, 12000), (18001, 19000), (27801, 28200)],
    7: [(5001, 6000), (12001, 13000), (19001, 20000), (28201, 28600)],
    8: [(6001, 7000), (13001, 14000), (20001, 21000), (28601, 29000)],
}
USER_NAMES = {2: "kimura", 3: "imai", 4: "umehara", 5: "endo", 6: "sato", 7: "tabe", 8: "matunaga"}


def validate_ranges():
    images = [image for ranges in ASSIGNMENTS.values() for low, high in ranges for image in range(low, high + 1)]
    if len(images) != 30000 or set(images) != set(range(1, 30001)):
        raise RuntimeError("画像範囲に重複・欠落があります。")


def assign(connection):
    from sqlalchemy import text
    validate_ranges()
    # 空テーブルも範囲ロックし、並行する初回割当による重複を防ぐ。
    for table in ("groups", "tasks"):
        rows = connection.execute(text(f"SELECT {table[:-1]}_id FROM `{table}` FOR UPDATE")).all()
        if rows:
            raise RuntimeError("既存グループまたはタスクがあるため、変更せず停止します。")
    users = connection.execute(text(
        "SELECT u.user_id,u.user_name,r.role_name FROM users u "
        "JOIN roles r ON r.role_id=u.role_id WHERE u.deleted_at IS NULL FOR UPDATE"
    )).all()
    actual = {user_id: (name, role) for user_id, name, role in users}
    if any(actual.get(user_id) != (name, "worker") for user_id, name in USER_NAMES.items()):
        raise RuntimeError("ユーザーID・名前・作業者権限が指定と一致しません。")
    state_id = connection.execute(text(
        "SELECT state_id FROM states WHERE state_name=:name AND deleted_at IS NULL FOR UPDATE"
    ), {"name": "未着手"}).scalar_one()
    now = datetime.now(UTC).replace(tzinfo=None)
    for user_id, ranges in ASSIGNMENTS.items():
        for low, high in ranges:
            result = connection.execute(text(
                "INSERT INTO `groups` (group_name,user_id,created_at,updated_at) "
                "VALUES (:name,:user_id,:now,:now)"
            ), {"name": f"{low:05d}-{high:05d}", "user_id": user_id, "now": now})
            connection.execute(text(
                "INSERT INTO tasks (group_id,image_id,state_id,created_at,updated_at) "
                "VALUES (:group_id,:image_id,:state_id,:now,:now)"
            ), [{"group_id": result.lastrowid, "image_id": image_id, "state_id": state_id, "now": now}
                for image_id in range(low, high + 1)])
    rows = connection.execute(text(
        "SELECT g.user_id,COUNT(DISTINCT g.group_id),COUNT(t.task_id) "
        "FROM `groups` g JOIN tasks t ON t.group_id=g.group_id GROUP BY g.user_id ORDER BY g.user_id"
    )).all()
    expected = [(uid, len(ranges), sum(high-low+1 for low, high in ranges)) for uid, ranges in ASSIGNMENTS.items()]
    if rows != expected:
        raise RuntimeError("登録後の割当件数が一致しません。")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="指定の割当をDBへ登録する")
    args = parser.parse_args()
    validate_ranges()
    for uid, ranges in ASSIGNMENTS.items():
        print(f"{uid} {USER_NAMES[uid]}: {len(ranges)}グループ / {sum(b-a+1 for a,b in ranges)}件")
    if not args.apply:
        print("確認のみ。登録する場合は --apply を指定してください。")
        return
    from app.database import engine
    if engine.url.drivername != "mysql+pymysql" or engine.url.database != "check_annotator":
        raise RuntimeError("対象はMySQLのcheck_annotatorに限定しています。")
    print(f"対象: {engine.url.host}:{engine.url.port or 3306}/{engine.url.database}")
    with engine.begin() as connection:
        assign(connection)
    print("完了: 34グループ・30000タスクを未着手で登録しました。")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        from set_user_password import error_message
        print(f"割当を停止しました: {error_message(error)}", file=sys.stderr)
        sys.exit(1)
