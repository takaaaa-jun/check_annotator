from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import (
    get_authenticated_user_id,
)
from app.database import get_db
from app.repositories.user_repository import (
    UserRepository,
)
from app.repositories.group_repository import GroupRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.error import ErrorResponse
from app.schemas.group import (
    GroupProgressResponse,
    GroupUserResponse,
    StateCountResponse,
    UserGroupsResponse,
)
from app.schemas.user import CurrentUserResponse
from app.schemas.task import (
    GroupTasksResponse,
    PaginationResponse,
    TaskGroupResponse,
    TaskResponse,
)
from app.services.group_service import GroupService
from app.services.user_service import UserService
from app.services.task_service import TaskService


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


@router.get(
    "/{user_id}/groups/{group_id}/tasks",
    response_model=GroupTasksResponse,
    responses={code: {"model": ErrorResponse} for code in [401, 403, 404, 422, 500]},
)
def get_group_tasks(
    user_id: int,
    group_id: int,
    state_id: Annotated[int | None, Query(ge=1)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1)] = 50,
    authenticated_user_id: int = Depends(get_authenticated_user_id),
    db: Session = Depends(get_db),
) -> GroupTasksResponse:
    if page_size not in {10, 50, 100}:
        raise RequestValidationError([])

    result = TaskService(
        UserRepository(db), GroupRepository(db), TaskRepository(db)
    ).get_group_tasks(
        authenticated_user_id, user_id, group_id, state_id, page, page_size
    )
    return GroupTasksResponse(
        group=TaskGroupResponse(
            group_id=result.group_id,
            group_name=result.group_name,
            user_id=result.user_id,
            user_name=result.user_name,
        ),
        tasks=[
            TaskResponse(
                task_id=task.task_id,
                image_id=task.image_id,
                state_id=task.state_id,
                state_name=task.state_name,
                updated_at=task.updated_at,
            )
            for task in result.tasks
        ],
        pagination=PaginationResponse(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )
