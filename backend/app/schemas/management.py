from datetime import datetime

from pydantic import BaseModel

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
