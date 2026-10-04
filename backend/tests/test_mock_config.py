import pytest

from app.core.config import (
    get_data_mode,
    validate_mock_mode,
)


def test_mock_mode_accepts_development_sqlite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )

    monkeypatch.setenv(
        "APP_DATA_MODE",
        "mock",
    )

    assert get_data_mode() == "mock"

    validate_mock_mode(
        "sqlite:////data/mock.db"
    )


def test_mock_mode_rejects_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )

    with pytest.raises(
        RuntimeError,
        match="only in development",
    ):
        validate_mock_mode(
            "sqlite:////data/mock.db"
        )


def test_mock_mode_rejects_non_sqlite_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )

    with pytest.raises(
        RuntimeError,
        match="requires a SQLite",
    ):
        validate_mock_mode(
            "mysql+pymysql://"
            "user:password@db/app"
        )