from datetime import datetime

from pydantic import BaseModel, Field


class TaskGroupResponse(BaseModel):
    group_id: int
    group_name: str
    user_id: int
    user_name: str


class TaskResponse(BaseModel):
    task_id: int
    image_id: int
    state_id: int
    state_name: str
    updated_at: datetime


class PaginationResponse(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class GroupTasksResponse(BaseModel):
    group: TaskGroupResponse
    tasks: list[TaskResponse]
    pagination: PaginationResponse


class TaskStateUpdateRequest(BaseModel):
    state_id: int = Field(ge=1)


class TaskStateResponse(BaseModel):
    task_id: int
    group_id: int | None
    image_id: int
    state_id: int
    state_name: str
    updated_at: datetime
