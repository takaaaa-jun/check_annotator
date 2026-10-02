from dataclasses import dataclass
from datetime import UTC, datetime
from math import ceil

from app.core.exceptions import (
    AuthenticationRequiredError,
    CommentNotFoundError,
    PermissionDeniedError,
    TaskNotFoundError,
)
from app.models.user import User
from app.repositories.comment_repository import CommentRecord, CommentRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class CreatedComment:
    comment_id: int
    task_id: int
    user_id: int
    user_name: str
    parent_id: int | None
    content: str
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class TaskComments:
    task_id: int
    comments: list[CommentRecord]
    page: int
    page_size: int
    total: int
    total_pages: int


class CommentService:
    def __init__(
        self,
        users: UserRepository,
        groups: GroupRepository,
        tasks: TaskRepository,
        comments: CommentRepository,
    ) -> None:
        self.users = users
        self.groups = groups
        self.tasks = tasks
        self.comments = comments

    def _authorize_task(self, authenticated_user_id: int, task_id: int) -> User:
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
        return user

    def get_task_comments(
        self,
        authenticated_user_id: int,
        task_id: int,
        page: int,
        page_size: int,
    ) -> TaskComments:
        self._authorize_task(authenticated_user_id, task_id)
        comments, total = self.comments.find_page(task_id, page, page_size)
        normalized = [
            CommentRecord(
                comment_id=comment.comment_id,
                user_id=comment.user_id,
                user_name=comment.user_name,
                parent_id=comment.parent_id,
                content=comment.content,
                created_at=(
                    comment.created_at.replace(tzinfo=UTC)
                    if comment.created_at.tzinfo is None
                    else comment.created_at.astimezone(UTC)
                ),
                updated_at=(
                    comment.updated_at.replace(tzinfo=UTC)
                    if comment.updated_at.tzinfo is None
                    else comment.updated_at.astimezone(UTC)
                ),
            )
            for comment in comments
        ]
        return TaskComments(
            task_id=task_id,
            comments=normalized,
            page=page,
            page_size=page_size,
            total=total,
            total_pages=ceil(total / page_size),
        )

    def create(
        self,
        authenticated_user_id: int,
        task_id: int,
        content: str,
        parent_id: int | None,
    ) -> CreatedComment:
        user = self._authorize_task(authenticated_user_id, task_id)

        if parent_id is not None:
            parent = self.comments.find_active_by_id(parent_id)
            if parent is None or parent.task_id != task_id:
                raise CommentNotFoundError

        now = datetime.now(UTC)
        comment = self.comments.create(
            task_id=task_id,
            user_id=user.user_id,
            parent_id=parent_id,
            content=content,
            created_at=now.replace(tzinfo=None),
        )
        return CreatedComment(
            comment_id=comment.comment_id,
            task_id=comment.task_id,
            user_id=comment.user_id,
            user_name=user.user_name,
            parent_id=comment.parent_id,
            content=comment.content,
            created_at=comment.created_at.replace(tzinfo=UTC),
            updated_at=comment.updated_at.replace(tzinfo=UTC),
        )
