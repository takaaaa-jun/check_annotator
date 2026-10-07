from unittest.mock import MagicMock

import pytest

from app.database import (
    build_database_url,
    build_engine_options,
    check_database_connection,
)


def test_build_database_url_escapes_credentials() -> None:
    database_url = build_database_url(
        {
            "DB_HOST": "192.0.2.10",
            "DB_PORT": "3307",
            "DB_NAME": "annotation/db",
            "DB_USER": "app user",
            "DB_PASSWORD": "p@ss:word",
        }
    )

    assert database_url == (
        "mysql+pymysql://app+user:p%40ss%3Aword"
        "@192.0.2.10:3307/annotation%2Fdb"
        "?charset=utf8mb4"
    )


def test_configured_database_url_takes_precedence() -> None:
    assert build_database_url(
        {
            "DATABASE_URL": "sqlite:////data/test.db",
        }
    ) == "sqlite:////data/test.db"


def test_mysql_engine_options_include_ssl_and_timeouts() -> None:
    options = build_engine_options(
        "mysql+pymysql://user:password@db/app",
        {
            "DB_CONNECT_TIMEOUT": "7",
            "DB_POOL_RECYCLE": "900",
            "DB_SSL_CA": "/run/secrets/mysql-ca.pem",
        },
    )

    assert options == {
        "pool_pre_ping": True,
        "pool_recycle": 900,
        "connect_args": {
            "connect_timeout": 7,
            "ssl": {
                "ca": "/run/secrets/mysql-ca.pem",
                "check_hostname": True,
            },
        },
    }


def test_sqlite_engine_options_remain_supported() -> None:
    assert build_engine_options(
        "sqlite:////data/test.db",
        {},
    ) == {
        "pool_pre_ping": True,
        "connect_args": {
            "check_same_thread": False,
        },
    }


@pytest.mark.parametrize(
    "variable_name",
    ["DB_CONNECT_TIMEOUT", "DB_POOL_RECYCLE"],
)
def test_engine_options_reject_invalid_positive_integers(
    variable_name: str,
) -> None:
    with pytest.raises(
        RuntimeError,
        match=f"{variable_name} must be a positive integer",
    ):
        build_engine_options(
            "mysql+pymysql://user:password@db/app",
            {variable_name: "0"},
        )


def test_check_database_connection_executes_query() -> None:
    database_engine = MagicMock()
    connection = (
        database_engine.connect.return_value.__enter__.return_value
    )

    check_database_connection(database_engine)

    database_engine.connect.assert_called_once_with()
    connection.execute.assert_called_once()
