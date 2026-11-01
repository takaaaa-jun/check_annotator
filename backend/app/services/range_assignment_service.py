import hashlib
import json
from datetime import UTC, datetime

from sqlalchemy import select, update

from app.core.exceptions import PermissionDeniedError, UserNotFoundError
from app.models.group import Group
from app.models.task import Task
from app.repositories.user_repository import UserRepository
from app.services.assignment_service import AssignmentConflict
from app.services.management_service import ManagementService


class RangeAssignmentService:
    def __init__(self, db):
        self.db = db

    def snapshot(self, lock=False):
        groups_query = select(Group).order_by(Group.group_id)
        tasks_query = select(Task).where(Task.deleted_at.is_(None)).order_by(Task.task_id)
        if lock:
            groups_query = groups_query.with_for_update()
            tasks_query = tasks_query.with_for_update()
        groups = list(self.db.scalars(groups_query.execution_options(populate_existing=True)))
        tasks = list(self.db.scalars(tasks_query.execution_options(populate_existing=True)))
        revision = hashlib.sha256(json.dumps([
            [(g.group_id, g.group_name, g.user_id, str(g.deleted_at), str(g.updated_at)) for g in groups],
            [(t.task_id, t.image_id, t.group_id) for t in tasks],
        ], separators=(",", ":")).encode()).hexdigest()
        return groups, tasks, revision

    def list(self, user_id):
        ManagementService(self.db).authorize(user_id, admin=True)
        groups, tasks, revision = self.snapshot()
        ranges = []
        for group in groups:
            if group.deleted_at is not None or group.user_id is None:
                continue
            ids = [t.image_id for t in tasks if t.group_id == group.group_id]
            if ids:
                ranges.append(dict(start_image_id=min(ids), end_image_id=max(ids), user_id=group.user_id))
        ids = [t.image_id for t in tasks]
        return dict(revision=revision, ranges=sorted(ranges, key=lambda r: r["start_image_id"]),
                    total_tasks=len(tasks), image_id_min=min(ids) if ids else None, image_id_max=max(ids) if ids else None)

    def save(self, user_id, payload):
        ManagementService(self.db).authorize(user_id, admin=True)
        ranges = sorted(payload.ranges, key=lambda r: r.start_image_id)
        previous_end = 0
        for item in ranges:
            if item.start_image_id > item.end_image_id:
                raise AssignmentConflict("開始画像IDは終了画像ID以下にしてください。変更していません。")
            if item.start_image_id <= previous_end:
                raise AssignmentConflict("画像IDの範囲が重複しています。変更していません。")
            previous_end = item.end_image_id
        users = UserRepository(self.db)
        for target in {r.user_id for r in ranges}:
            user = users.find_active_by_id(target)
            if user is None:
                raise UserNotFoundError
            if user.role.role_name == "admin" or user.role.deleted_at is not None:
                raise PermissionDeniedError
        try:
            groups, tasks, revision = self.snapshot(lock=True)
            if revision != payload.revision:
                raise AssignmentConflict("割り当てや対象画像が変更されています。「最新に更新」して選び直してください。変更していません。")
            destinations = []
            used_task_ids = set()
            for item in ranges:
                selected = [t for t in tasks if item.start_image_id <= t.image_id <= item.end_image_id]
                if len({t.image_id for t in selected}) != item.end_image_id - item.start_image_id + 1:
                    raise AssignmentConflict("範囲内に存在しない画像IDがあります。変更していません。")
                if len(selected) != len({t.image_id for t in selected}):
                    raise AssignmentConflict("同じ画像IDのタスクが複数あります。データを確認してください。変更していません。")
                destinations.append((f"{item.start_image_id:05d}-{item.end_image_id:05d}", item.user_id, selected))
                used_task_ids.update(t.task_id for t in selected)
            remaining = [t for t in tasks if t.task_id not in used_task_ids]
            if remaining:
                destinations.append(("未割り当て", None, remaining))
            now = datetime.now(UTC).replace(tzinfo=None)
            by_name = {g.group_name: g for g in groups}
            keep = set()
            for name, owner, selected in destinations:
                group = by_name.get(name)
                if group is None:
                    group = Group(group_name=name, user_id=owner, created_at=now, updated_at=now)
                    self.db.add(group)
                    self.db.flush()
                group.user_id, group.deleted_at, group.updated_at = owner, None, now
                keep.add(group.group_id)
                # Only membership changes; task identity, state, timestamps and comments remain intact.
                task_ids = [t.task_id for t in selected]
                for offset in range(0, len(task_ids), 500):
                    self.db.execute(update(Task).where(Task.task_id.in_(task_ids[offset:offset + 500]))
                                    .values(group_id=group.group_id).execution_options(synchronize_session=False))
            for group in groups:
                if group.group_id not in keep and group.deleted_at is None:
                    group.user_id, group.deleted_at, group.updated_at = None, now, now
            self.db.commit()
            self.db.expire_all()
        except Exception:
            self.db.rollback()
            raise
        return self.list(user_id)
