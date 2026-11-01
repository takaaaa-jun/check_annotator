from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_authenticated_user_id
from app.database import get_db
from app.schemas.management import AdminOverviewResponse, CommentActivityPage
from app.services.management_service import ManagementService
from app.schemas.management import AssignmentList, AssignmentRequest
from app.services.assignment_service import AssignmentService, AssignmentConflict
from app.core.exceptions import error_response
from app.schemas.management import RangeAssignmentList, RangeAssignmentRequest
from app.services.range_assignment_service import RangeAssignmentService

router = APIRouter(prefix="/api", tags=["management"])


@router.get("/admin/assignment-ranges", response_model=RangeAssignmentList)
def assignment_ranges(user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db)):
    return RangeAssignmentService(db).list(user_id)


@router.post("/admin/assignment-ranges", response_model=RangeAssignmentList)
def save_assignment_ranges(payload: RangeAssignmentRequest, user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db)):
    try:
        return RangeAssignmentService(db).save(user_id, payload)
    except AssignmentConflict as error:
        return error_response(409, "ASSIGNMENT_CONFLICT", str(error))


@router.get("/admin/assignments", response_model=AssignmentList)
def assignments(user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db)):
    return AssignmentService(db).list(user_id)


@router.post("/admin/assignments", response_model=AssignmentList)
def save_assignments(payload: AssignmentRequest, user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db)):
    try:
        return AssignmentService(db).save(user_id, payload.assignments)
    except AssignmentConflict as error:
        return error_response(409, "ASSIGNMENT_CONFLICT", str(error))


@router.get("/admin/overview", response_model=AdminOverviewResponse)
def overview(user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db)):
    return ManagementService(db).overview(user_id)


@router.get("/admin/comments", response_model=CommentActivityPage)
def comments(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    worker_id: Annotated[int | None, Query(ge=1)] = None,
    unanswered: bool = False,
    user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db),
):
    return ManagementService(db).comments(user_id, page, page_size, worker_id, unanswered)


@router.get("/users/me/replies", response_model=CommentActivityPage)
def replies(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    user_id: int = Depends(get_authenticated_user_id), db: Session = Depends(get_db),
):
    return ManagementService(db).replies(user_id, page, page_size)
