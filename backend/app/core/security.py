import os
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash


JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 28_800

password_hash = PasswordHash.recommended()


class InvalidAccessTokenError(Exception):
    pass


def get_auth_secret_key() -> str:
    secret_key = os.getenv("AUTH_SECRET_KEY", "")
    if not secret_key:
        raise RuntimeError("AUTH_SECRET_KEY must be configured")
    return secret_key


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    try:
        return password_hash.verify(
            plain_password,
            hashed_password,
        )
    except Exception:
        return False


def create_access_token(
    user_id: int,
    now: datetime | None = None,
) -> str:
    issued_at = now or datetime.now(UTC)

    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at
        + timedelta(seconds=ACCESS_TOKEN_EXPIRE_SECONDS),
    }

    return jwt.encode(
        payload,
        get_auth_secret_key(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(
    access_token: str,
) -> int:
    try:
        payload = jwt.decode(
            access_token,
            get_auth_secret_key(),
            algorithms=[JWT_ALGORITHM],
            options={
                "require": [
                    "sub",
                    "iat",
                    "exp",
                ]
            },
        )
    except jwt.PyJWTError as exc:
        raise InvalidAccessTokenError from exc

    subject = payload.get("sub")

    if not isinstance(subject, str):
        raise InvalidAccessTokenError

    try:
        user_id = int(subject)
    except ValueError as exc:
        raise InvalidAccessTokenError from exc

    if user_id <= 0:
        raise InvalidAccessTokenError

    return user_id
