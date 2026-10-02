from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.core.exceptions import error_response
from app.core.security import ACCESS_TOKEN_EXPIRE_SECONDS
from app.database import get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LoginUserResponse,
)
from app.schemas.error import ErrorResponse
from app.services.auth_service import (
    AuthService,
    InvalidCredentialsError,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)


@router.post(
    "/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    service = AuthService(
        UserRepository(db)
    )

    try:
        result = service.login(
            payload.user_name,
            payload.password,
        )
    except InvalidCredentialsError:
        return error_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message=(
                "ユーザー名またはパスワードが"
                "正しくありません"
            ),
        )

    response.set_cookie(
        key="access_token",
        value=result.access_token,
        max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
        path="/",
        secure=False,
        httponly=False,
        samesite="lax",
    )

    return LoginResponse(
        user=LoginUserResponse(
            user_id=result.user.user_id,
            user_name=result.user.user_name,
            role_name=result.user.role_name,
        )
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
)
def logout(response: Response) -> None:
    response.delete_cookie(
        key="access_token",
        path="/",
        secure=False,
        httponly=False,
        samesite="lax",
    )
