from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    StateNotFoundError,
    TaskNotFoundError,
)
from app.repositories.group_repository import GroupRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class UpdatedTaskState:
    task_id: int
    group_id: int | None
    image_id: int
    state_id: int
    state_name: str
    updated_at: datetime


class TaskStateService:
    def __init__(self, users: UserRepository, groups: GroupRepository, tasks: TaskRepository) -> None:
        self.users = users
        self.groups = groups
        self.tasks = tasks

    def update(self, authenticated_user_id: int, task_id: int, state_id: int) -> UpdatedTaskState:
        user = self.users.find_active_by_id(authenticated_user_id)
        if user is None:
            raise AuthenticationRequiredError
        found = self.tasks.find_active_with_state(task_id)
        if found is None:
            raise TaskNotFoundError
        task, _ = found
        group = None if task.group_id is None else self.groups.find_active_by_id(task.group_id)
        if group is None:
            raise TaskNotFoundError
        if user.role.role_name != "admin" and group.user_id != user.user_id:
            raise PermissionDeniedError
        if not self.tasks.state_exists(state_id):
            raise StateNotFoundError
        now = datetime.now(UTC)
        state_name = self.tasks.update_state(task, state_id, now.replace(tzinfo=None))
        return UpdatedTaskState(
            task_id=task.task_id,
            group_id=task.group_id,
            image_id=task.image_id,
            state_id=task.state_id,
            state_name=state_name,
            updated_at=now,
        )
