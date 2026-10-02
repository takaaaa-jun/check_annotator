from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class CommentCreateRequest(BaseModel):
    content: str = Field(min_length=1, max_length=2000)
    parent_id: int | None = Field(default=None, ge=1)

    @field_validator("content", mode="before")
    @classmethod
    def trim_content(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class CommentResponse(BaseModel):
    comment_id: int
    task_id: int
    user_id: int
    user_name: str
    parent_id: int | None
    content: str
    created_at: datetime
    updated_at: datetime


class CommentListItemResponse(BaseModel):
    comment_id: int
    user_id: int
    user_name: str
    parent_id: int | None
    content: str
    created_at: datetime
    updated_at: datetime


class CommentPaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class TaskCommentsResponse(BaseModel):
    task_id: int
    comments: list[CommentListItemResponse]
    pagination: CommentPaginationResponse
