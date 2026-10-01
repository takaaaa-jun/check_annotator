import os
from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash


JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 28_800

password_hash = PasswordHash.recommended()


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
        os.environ["AUTH_SECRET_KEY"],
        algorithm=JWT_ALGORITHM,
    )