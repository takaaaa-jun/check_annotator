import os


DATA_MODE_DATABASE = "database"
DATA_MODE_MOCK = "mock"
SUPPORTED_DATA_MODES = {
    DATA_MODE_DATABASE,
    DATA_MODE_MOCK,
}


def get_cors_origins() -> list[str]:
    return [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:3000",
        ).split(",")
        if origin.strip()
    ]


def get_app_environment() -> str:
    return os.getenv(
        "APP_ENV",
        "development",
    ).strip().lower()


def get_data_mode() -> str:
    data_mode = os.getenv(
        "APP_DATA_MODE",
        DATA_MODE_DATABASE,
    ).strip().lower()

    if data_mode not in SUPPORTED_DATA_MODES:
        raise RuntimeError(
            "APP_DATA_MODE must be either "
            "'database' or 'mock'"
        )

    return data_mode


def validate_mock_mode(
    database_url: str,
) -> None:
    if get_app_environment() != "development":
        raise RuntimeError(
            "Mock data mode is available "
            "only in development"
        )

    if not database_url.startswith("sqlite:"):
        raise RuntimeError(
            "Mock data mode requires "
            "a SQLite DATABASE_URL"
        )