from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.routers.auth import router as auth_router
from app.api.routers.users import router as users_router
from app.api.routers.tasks import router as tasks_router
from app.core.exceptions import (
    AuthenticationRequiredError,
    GroupNotFoundError,
    PermissionDeniedError,
    StateNotFoundError,
    TaskNotFoundError,
    UserNotFoundError,
    authentication_exception_handler,
    group_not_found_exception_handler,
    internal_exception_handler,
    permission_exception_handler,
    state_not_found_exception_handler,
    task_not_found_exception_handler,
    user_not_found_exception_handler,
    validation_exception_handler,
)


app = FastAPI()

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
app.add_exception_handler(GroupNotFoundError, group_not_found_exception_handler)
app.add_exception_handler(StateNotFoundError, state_not_found_exception_handler)
app.add_exception_handler(TaskNotFoundError, task_not_found_exception_handler)
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
    return {"status": "ok"}
