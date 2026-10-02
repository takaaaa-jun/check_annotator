from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from app.api.routers.auth import (
    router as auth_router,
)
from app.api.routers.users import (
    router as users_router,
)
from app.core.exceptions import (
    AuthenticationRequiredError,
    authentication_exception_handler,
    internal_exception_handler,
    validation_exception_handler,
)


app = FastAPI()

app.add_exception_handler(
    AuthenticationRequiredError,
    authentication_exception_handler,
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


@app.get("/health")
def health():
    return {"status": "ok"}