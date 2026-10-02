from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_authenticated_user_id,
)
from app.database import get_db
from app.repositories.user_repository import (
    UserRepository,
)
from app.schemas.error import ErrorResponse
from app.schemas.user import CurrentUserResponse
from app.services.user_service import UserService


router = APIRouter(
    prefix="/api/users",
    tags=["users"],
)


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_current_user(
    user_id: int = Depends(
        get_authenticated_user_id
    ),
    db: Session = Depends(get_db),
) -> CurrentUserResponse:
    service = UserService(
        UserRepository(db)
    )

    user = service.get_current_user(
        user_id
    )

    return CurrentUserResponse(
        user_id=user.user_id,
        user_name=user.user_name,
        role_id=user.role_id,
        role_name=user.role_name,
        login_at=user.login_at,
    )