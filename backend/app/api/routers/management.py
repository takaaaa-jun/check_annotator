from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import get_authenticated_user_id
from app.database import get_db
from app.schemas.management import AdminOverviewResponse, CommentActivityPage
from app.services.management_service import ManagementService

router = APIRouter(prefix="/api", tags=["management"])


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
