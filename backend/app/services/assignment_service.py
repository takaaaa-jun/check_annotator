from datetime import UTC, datetime
from sqlalchemy import func, select, update
from app.core.exceptions import GroupNotFoundError, PermissionDeniedError, UserNotFoundError
from app.models.group import Group
from app.models.state import State
from app.models.task import Task
from app.repositories.user_repository import UserRepository
from app.services.management_service import ManagementService


class AssignmentConflict(Exception):
    pass


class AssignmentService:
    def __init__(self, db):
        self.db = db

    def list(self, user_id):
        ManagementService(self.db).authorize(user_id, admin=True)
        tasks = (select(Task.group_id, func.count(Task.task_id).label("total_count"),
                        func.min(Task.image_id).label("image_id_min"), func.max(Task.image_id).label("image_id_max"))
                 .join(State, State.state_id == Task.state_id)
                 .where(Task.deleted_at.is_(None), State.deleted_at.is_(None)).group_by(Task.group_id).subquery())
        rows = self.db.execute(select(Group, tasks.c.total_count, tasks.c.image_id_min, tasks.c.image_id_max)
            .outerjoin(tasks, tasks.c.group_id == Group.group_id)
            .where(Group.deleted_at.is_(None)).order_by(Group.group_id)).all()
        return {"groups": [dict(group_id=row[0].group_id, group_name=row[0].group_name,
                    user_id=row[0].user_id, total_count=row.total_count or 0,
                    image_id_min=row.image_id_min, image_id_max=row.image_id_max) for row in rows]}

    def save(self, user_id, assignments):
        ManagementService(self.db).authorize(user_id, admin=True)
        if len({item.group_id for item in assignments}) != len(assignments):
            raise AssignmentConflict("同じグループが重複しています。変更していません。")
        users = UserRepository(self.db)
        for target in {item.user_id for item in assignments if item.user_id is not None}:
            user = users.find_active_by_id(target)
            if user is None:
                raise UserNotFoundError
            if user.role.role_name == "admin" or user.role.deleted_at is not None:
                raise PermissionDeniedError
        try:
            groups = {group.group_id: group for group in self.db.scalars(select(Group)
                .where(Group.group_id.in_([item.group_id for item in assignments]), Group.deleted_at.is_(None))
                .order_by(Group.group_id).with_for_update())}
            for item in assignments:
                group = groups.get(item.group_id)
                if group is None:
                    raise GroupNotFoundError
                if group.user_id != item.expected_user_id:
                    raise AssignmentConflict("担当者が別の操作で変更されています。「最新に更新」して選び直してください。変更していません。")
            now = datetime.now(UTC).replace(tzinfo=None)
            for item in assignments:
                result = self.db.execute(update(Group).where(Group.group_id == item.group_id,
                    Group.deleted_at.is_(None), Group.user_id == item.expected_user_id)
                    .values(user_id=item.user_id, updated_at=now).execution_options(synchronize_session=False))
                if result.rowcount != 1:
                    raise AssignmentConflict("担当者が同時に変更されたため、変更を取り消しました。")
            self.db.commit()
            self.db.expire_all()
        except Exception:
            self.db.rollback()
            raise
        return self.list(user_id)
