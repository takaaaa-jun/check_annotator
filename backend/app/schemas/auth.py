from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    user_name: str = Field(
        min_length=1,
        max_length=50,
    )

    password: str = Field(
        min_length=1,
        max_length=255,
    )


class LoginUserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: int
    user_name: str
    role_name: str


class LoginResponse(BaseModel):
    user: LoginUserResponse