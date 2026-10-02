from pydantic import BaseModel


class GroupUserResponse(BaseModel):
    user_id: int
    user_name: str


class StateCountResponse(BaseModel):
    state_id: int
    state_name: str
    count: int


class GroupProgressResponse(BaseModel):
    group_id: int
    group_name: str
    image_id_min: int | None
    image_id_max: int | None
    total_count: int
    state_counts: list[StateCountResponse]


class UserGroupsResponse(BaseModel):
    user: GroupUserResponse
    groups: list[GroupProgressResponse]
