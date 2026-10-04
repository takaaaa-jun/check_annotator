from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import (
    RequestValidationError,
)
from fastapi.middleware.cors import (
    CORSMiddleware,
)

from app.api.routers.auth import (
    router as auth_router,
)
from app.api.routers.tasks import (
    router as tasks_router,
)
from app.api.routers.users import (
    router as users_router,
)
from app.core.config import get_cors_origins
from app.core.exceptions import (
    AuthenticationRequiredError,
    CommentNotFoundError,
    GroupNotFoundError,
    PermissionDeniedError,
    StateNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
    authentication_exception_handler,
    comment_not_found_exception_handler,
    group_not_found_exception_handler,
    internal_exception_handler,
    permission_exception_handler,
    state_not_found_exception_handler,
    task_not_found_exception_handler,
    user_not_found_exception_handler,
    validation_exception_handler,
)
from app.mock.startup import (
    initialize_mock_database,
)


@asynccontextmanager
async def lifespan(
    _app: FastAPI,
):
    initialize_mock_database()
    yield


app = FastAPI(
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(
    AuthenticationRequiredError,
    authentication_exception_handler,
)

app.add_exception_handler(
    PermissionDeniedError,
    permission_exception_handler,
)

app.add_exception_handler(
    UserNotFoundError,
    user_not_found_exception_handler,
)

app.add_exception_handler(
    GroupNotFoundError,
    group_not_found_exception_handler,
)

app.add_exception_handler(
    StateNotFoundError,
    state_not_found_exception_handler,
)

app.add_exception_handler(
    TaskNotFoundError,
    task_not_found_exception_handler,
)

app.add_exception_handler(
    CommentNotFoundError,
    comment_not_found_exception_handler,
)

app.add_exception_handler(
    RequestValidationError,
    validation_exception_handler,
)

app.add_exception_handler(
    Exception,
    internal_exception_handler,
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(tasks_router)


@app.get("/health")
def health():
    return {
        "status": "ok",
    }
