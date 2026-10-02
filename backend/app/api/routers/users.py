from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_authenticated_user_id,
)
from app.database import get_db
from app.repositories.user_repository import (
    UserRepository,
)
from app.repositories.group_repository import GroupRepository
from app.schemas.error import ErrorResponse
from app.schemas.group import (
    GroupProgressResponse,
    GroupUserResponse,
    StateCountResponse,
    UserGroupsResponse,
)
from app.schemas.user import CurrentUserResponse
from app.services.group_service import GroupService
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


@router.get(
    "/{user_id}/groups",
    response_model=UserGroupsResponse,
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_user_groups(
    user_id: int,
    authenticated_user_id: int = Depends(get_authenticated_user_id),
    db: Session = Depends(get_db),
) -> UserGroupsResponse:
    result = GroupService(
        UserRepository(db),
        GroupRepository(db),
    ).get_user_groups(
        authenticated_user_id,
        user_id,
    )

    return UserGroupsResponse(
        user=GroupUserResponse(
            user_id=result.user_id,
            user_name=result.user_name,
        ),
        groups=[
            GroupProgressResponse(
                group_id=group.group_id,
                group_name=group.group_name,
                image_id_min=group.image_id_min,
                image_id_max=group.image_id_max,
                total_count=group.total_count,
                state_counts=[
                    StateCountResponse(
                        state_id=state.state_id,
                        state_name=state.state_name,
                        count=state.count,
                    )
                    for state in group.state_counts
                ],
            )
            for group in result.groups
        ],
    )
