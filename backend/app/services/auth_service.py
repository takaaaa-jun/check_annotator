from dataclasses import dataclass
from datetime import UTC, datetime

from app.core.security import (
    create_access_token,
    verify_password,
)
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class AuthenticatedUser:
    user_id: int
    user_name: str
    role_name: str


@dataclass(frozen=True)
class LoginResult:
    access_token: str
    user: AuthenticatedUser


class InvalidCredentialsError(Exception):
    pass


class AuthService:
    def __init__(
        self,
        user_repository: UserRepository,
    ) -> None:
        self.user_repository = user_repository

    def login(
        self,
        user_name: str,
        password: str,
    ) -> LoginResult:
        user = self.user_repository.find_active_by_user_name(
            user_name
        )

        if user is None or not verify_password(
            password,
            user.password_hash,
        ):
            raise InvalidCredentialsError

        now = datetime.now(UTC)

        self.user_repository.update_login_at(
            user,
            now.replace(tzinfo=None),
        )

        return LoginResult(
            access_token=create_access_token(
                user.user_id,
                now=now,
            ),
            user=AuthenticatedUser(
                user_id=user.user_id,
                user_name=user.user_name,
                role_name=user.role.role_name,
            ),
        )