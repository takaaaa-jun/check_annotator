from datetime import datetime

from pydantic import BaseModel, Field
from typing import Annotated

from app.schemas.group import StateCountResponse
from app.schemas.task import PaginationResponse


class WorkerProgressResponse(BaseModel):
    user_id: int
    user_name: str
    group_count: int
    total_count: int
    completed_count: int
    pending_comments: int
    state_counts: list[StateCountResponse]


class AdminOverviewResponse(BaseModel):
    workers: list[WorkerProgressResponse]
    total_tasks: int
    completed_tasks: int
    pending_comments: int
    unassigned_groups: int = 0
    unassigned_tasks: int = 0


class CommentActivityResponse(BaseModel):
    comment_id: int
    task_id: int
    image_id: int
    group_id: int
    group_name: str
    worker_id: int
    worker_name: str
    user_id: int
    user_name: str
    author_role: str
    parent_id: int | None
    parent_content: str | None
    content: str
    created_at: datetime
    updated_at: datetime
    has_admin_reply: bool


class CommentActivityPage(BaseModel):
    comments: list[CommentActivityResponse]
    pagination: PaginationResponse


class AssignmentGroup(BaseModel):
    group_id: int
    group_name: str
    user_id: int | None
    total_count: int
    image_id_min: int | None
    image_id_max: int | None


class AssignmentList(BaseModel):
    groups: list[AssignmentGroup]


class AssignmentChange(BaseModel):
    group_id: Annotated[int, Field(gt=0, strict=True)]
    user_id: Annotated[int, Field(gt=0, strict=True)] | None
    expected_user_id: Annotated[int, Field(gt=0, strict=True)] | None


class AssignmentRequest(BaseModel):
    assignments: list[AssignmentChange] = Field(min_length=1, max_length=1000)
