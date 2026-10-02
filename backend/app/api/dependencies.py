from fastapi import Cookie

from app.core.exceptions import (
    AuthenticationRequiredError,
)
from app.core.security import (
    InvalidAccessTokenError,
    decode_access_token,
)


def get_authenticated_user_id(
    access_token: str | None = Cookie(
        default=None,
    ),
) -> int:
    if access_token is None:
        raise AuthenticationRequiredError

    try:
        return decode_access_token(
            access_token
        )
    except InvalidAccessTokenError as exc:
        raise AuthenticationRequiredError from exc