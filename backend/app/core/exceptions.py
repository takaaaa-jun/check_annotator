from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class AuthenticationRequiredError(Exception):
    pass


class PermissionDeniedError(Exception):
    pass


class UserNotFoundError(Exception):
    pass


class GroupNotFoundError(Exception):
    pass


class StateNotFoundError(Exception):
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


async def permission_exception_handler(
    request: Request,
    exc: PermissionDeniedError,
) -> JSONResponse:
    return error_response(
        status_code=403,
        code="PERMISSION_DENIED",
        message="アクセス権限がありません",
    )


async def user_not_found_exception_handler(
    request: Request,
    exc: UserNotFoundError,
) -> JSONResponse:
    return error_response(
        status_code=404,
        code="USER_NOT_FOUND",
        message="指定されたユーザーが存在しません",
    )


async def group_not_found_exception_handler(
    request: Request,
    exc: GroupNotFoundError,
) -> JSONResponse:
    return error_response(404, "GROUP_NOT_FOUND", "指定されたグループが存在しません")


async def state_not_found_exception_handler(
    request: Request,
    exc: StateNotFoundError,
) -> JSONResponse:
    return error_response(404, "STATE_NOT_FOUND", "指定された状態が存在しません")


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
