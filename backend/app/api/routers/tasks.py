from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.api.dependencies import get_authenticated_user_id
from app.database import get_db
from app.repositories.comment_repository import CommentRepository
from app.repositories.group_repository import GroupRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.comment import (
    CommentCreateRequest,
    CommentListItemResponse,
    CommentPaginationResponse,
    CommentResponse,
    TaskCommentsResponse,
)
from app.schemas.error import ErrorResponse
from app.schemas.task import TaskStateResponse, TaskStateUpdateRequest
from app.services.comment_service import CommentService
from app.services.task_state_service import TaskStateService


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get(
    "/{task_id}/comments",
    response_model=TaskCommentsResponse,
    responses={code: {"model": ErrorResponse} for code in [401, 403, 404, 422, 500]},
)
def get_task_comments(
    task_id: int,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, json_schema_extra={"enum": [10, 50, 100]}),
    ] = 50,
    authenticated_user_id: int = Depends(get_authenticated_user_id),
    db: Session = Depends(get_db),
) -> TaskCommentsResponse:
    if page_size not in {10, 50, 100}:
        raise RequestValidationError([])
    result = CommentService(
        UserRepository(db),
        GroupRepository(db),
        TaskRepository(db),
        CommentRepository(db),
    ).get_task_comments(authenticated_user_id, task_id, page, page_size)
    return TaskCommentsResponse(
        task_id=result.task_id,
        comments=[CommentListItemResponse(**comment.__dict__) for comment in result.comments],
        pagination=CommentPaginationResponse(
            page=result.page,
            page_size=result.page_size,
            total=result.total,
            total_pages=result.total_pages,
        ),
    )


@router.post(
    "/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    responses={code: {"model": ErrorResponse} for code in [401, 403, 404, 422, 500]},
)
def create_task_comment(
    task_id: int,
    payload: CommentCreateRequest,
    authenticated_user_id: int = Depends(get_authenticated_user_id),
    db: Session = Depends(get_db),
) -> CommentResponse:
    result = CommentService(
        UserRepository(db),
        GroupRepository(db),
        TaskRepository(db),
        CommentRepository(db),
    ).create(
        authenticated_user_id,
        task_id,
        payload.content,
        payload.parent_id,
    )
    return CommentResponse(**result.__dict__)


@router.patch(
    "/{task_id}/state",
    response_model=TaskStateResponse,
    responses={code: {"model": ErrorResponse} for code in [401, 403, 404, 422, 500]},
)
def update_task_state(
    task_id: int,
    payload: TaskStateUpdateRequest,
    authenticated_user_id: int = Depends(get_authenticated_user_id),
    db: Session = Depends(get_db),
) -> TaskStateResponse:
    result = TaskStateService(
        UserRepository(db), GroupRepository(db), TaskRepository(db)
    ).update(authenticated_user_id, task_id, payload.state_id)
    return TaskStateResponse(**result.__dict__)
