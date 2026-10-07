import os
from collections.abc import Mapping
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker


DEFAULT_DB_PORT = "3306"
DEFAULT_CONNECT_TIMEOUT = 5
DEFAULT_POOL_RECYCLE = 1800


def _positive_integer(
    value: str,
    variable_name: str,
) -> int:
    try:
        parsed_value = int(value)
    except ValueError as error:
        raise RuntimeError(
            f"{variable_name} must be a positive integer"
        ) from error

    if parsed_value <= 0:
        raise RuntimeError(
            f"{variable_name} must be a positive integer"
        )

    return parsed_value


def build_database_url(
    environment: Mapping[str, str] = os.environ,
) -> str:
    configured_url = environment.get(
        "DATABASE_URL",
        "",
    ).strip()
    if configured_url:
        return configured_url

    db_user = quote_plus(
        environment["DB_USER"]
    )
    db_password = quote_plus(
        environment["DB_PASSWORD"]
    )
    db_host = environment["DB_HOST"].strip()
    db_port = environment.get(
        "DB_PORT",
        DEFAULT_DB_PORT,
    ).strip()
    db_name = quote_plus(
        environment["DB_NAME"]
    )

    return (
        f"mysql+pymysql://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
        "?charset=utf8mb4"
    )


def build_engine_options(
    database_url: str,
    environment: Mapping[str, str] = os.environ,
) -> dict[str, object]:
    engine_options: dict[str, object] = {
        "pool_pre_ping": True,
    }

    if database_url.startswith("sqlite:"):
        engine_options["connect_args"] = {
            "check_same_thread": False,
        }
        return engine_options

    connect_timeout = _positive_integer(
        environment.get(
            "DB_CONNECT_TIMEOUT",
            str(DEFAULT_CONNECT_TIMEOUT),
        ),
        "DB_CONNECT_TIMEOUT",
    )
    pool_recycle = _positive_integer(
        environment.get(
            "DB_POOL_RECYCLE",
            str(DEFAULT_POOL_RECYCLE),
        ),
        "DB_POOL_RECYCLE",
    )
    connect_args: dict[str, object] = {
        "connect_timeout": connect_timeout,
    }
    ssl_ca = environment.get(
        "DB_SSL_CA",
        "",
    ).strip()
    if ssl_ca:
        connect_args["ssl"] = {
            "ca": ssl_ca,
            "check_hostname": True,
        }

    engine_options["connect_args"] = connect_args
    engine_options["pool_recycle"] = pool_recycle
    return engine_options


database_url = build_database_url()
engine_options = build_engine_options(database_url)

engine = create_engine(
    database_url,
    **engine_options,
)


if database_url.startswith("sqlite:"):

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(
        dbapi_connection,
        _connection_record,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )
        cursor.close()


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def check_database_connection(
    database_engine: Engine = engine,
) -> None:
    with database_engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
