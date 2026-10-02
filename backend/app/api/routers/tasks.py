from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_authenticated_user_id
from app.database import get_db
from app.repositories.group_repository import GroupRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.error import ErrorResponse
from app.schemas.task import TaskStateResponse, TaskStateUpdateRequest
from app.services.task_state_service import TaskStateService


router = APIRouter(prefix="/api/tasks", tags=["tasks"])


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
