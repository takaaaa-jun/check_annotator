from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AuthenticationRequiredError(Exception):
    pass


def error_response(
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


async def authentication_exception_handler(
    request: Request,
    exc: AuthenticationRequiredError,
) -> JSONResponse:
    return error_response(
        status_code=401,
        code="AUTHENTICATION_REQUIRED",
        message="認証が必要です",
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="入力値が正しくありません",
    )


async def internal_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    return error_response(
        status_code=500,
        code="INTERNAL_SERVER_ERROR",
        message="サーバー内部でエラーが発生しました",
    )