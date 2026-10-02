from dataclasses import dataclass
from datetime import UTC
from math import ceil

from app.core.exceptions import (
    AuthenticationRequiredError,
    GroupNotFoundError,
    PermissionDeniedError,
    StateNotFoundError,
    UserNotFoundError,
)
from app.repositories.group_repository import GroupRepository
from app.repositories.task_repository import TaskRecord, TaskRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class GroupTasks:
    group_id: int
    group_name: str
    user_id: int
    user_name: str
    tasks: list[TaskRecord]
    page: int
    page_size: int
    total: int
    total_pages: int


class TaskService:
    def __init__(self, users: UserRepository, groups: GroupRepository, tasks: TaskRepository) -> None:
        self.users = users
        self.groups = groups
        self.tasks = tasks

    def get_group_tasks(self, authenticated_user_id: int, user_id: int, group_id: int,
                        state_id: int | None, page: int, page_size: int) -> GroupTasks:
        authenticated = self.users.find_active_by_id(authenticated_user_id)
        if authenticated is None:
            raise AuthenticationRequiredError
        if authenticated.role.role_name != "admin" and authenticated_user_id != user_id:
            raise PermissionDeniedError
        user = self.users.find_active_by_id(user_id)
        if user is None:
            raise UserNotFoundError
        group = self.groups.find_active_by_id(group_id)
        if group is None or group.user_id != user_id:
            raise GroupNotFoundError
        if state_id is not None and not self.tasks.state_exists(state_id):
            raise StateNotFoundError
        tasks, total = self.tasks.find_page(group_id, state_id, page, page_size)
        normalized = [
            TaskRecord(
                task_id=task.task_id,
                image_id=task.image_id,
                state_id=task.state_id,
                state_name=task.state_name,
                updated_at=(task.updated_at.replace(tzinfo=UTC) if task.updated_at.tzinfo is None
                            else task.updated_at.astimezone(UTC)),
            )
            for task in tasks
        ]
        return GroupTasks(group.group_id, group.group_name, user.user_id, user.user_name,
                          normalized, page, page_size, total, ceil(total / page_size))
