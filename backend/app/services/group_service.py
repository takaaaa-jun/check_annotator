from dataclasses import dataclass

from app.core.exceptions import (
    AuthenticationRequiredError,
    PermissionDeniedError,
    UserNotFoundError,
)
from app.repositories.group_repository import GroupProgressRecord, GroupRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class UserGroups:
    user_id: int
    user_name: str
    groups: list[GroupProgressRecord]


class GroupService:
    def __init__(
        self,
        user_repository: UserRepository,
        group_repository: GroupRepository,
    ) -> None:
        self.user_repository = user_repository
        self.group_repository = group_repository

    def get_user_groups(
        self,
        authenticated_user_id: int,
        target_user_id: int,
    ) -> UserGroups:
        authenticated_user = self.user_repository.find_active_by_id(
            authenticated_user_id
        )
        if authenticated_user is None:
            raise AuthenticationRequiredError

        if (
            authenticated_user.role.role_name != "admin"
            and authenticated_user_id != target_user_id
        ):
            raise PermissionDeniedError

        target_user = self.user_repository.find_active_by_id(target_user_id)
        if target_user is None:
            raise UserNotFoundError

        return UserGroups(
            user_id=target_user.user_id,
            user_name=target_user.user_name,
            groups=self.group_repository.find_progress_by_user_id(
                target_user_id
            ),
        )
