from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.exceptions import (
    AuthenticationRequiredError,
)
from app.repositories.user_repository import (
    UserRepository,
)


@dataclass(frozen=True)
class CurrentUser:
    user_id: int
    user_name: str
    role_id: int
    role_name: str
    login_at: datetime | None


class UserService:
    def __init__(
        self,
        user_repository: UserRepository,
    ) -> None:
        self.user_repository = user_repository

    def get_current_user(
        self,
        user_id: int,
    ) -> CurrentUser:
        user = self.user_repository.find_active_by_id(
            user_id
        )

        if user is None:
            raise AuthenticationRequiredError

        login_at = user.login_at

        if (
            login_at is not None
            and login_at.tzinfo is None
        ):
            login_at = login_at.replace(
                tzinfo=UTC
            )
        elif login_at is not None:
            login_at = login_at.astimezone(
                UTC
            )

        return CurrentUser(
            user_id=user.user_id,
            user_name=user.user_name,
            role_id=user.role_id,
            role_name=user.role.role_name,
            login_at=login_at,
        )