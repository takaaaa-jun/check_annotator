import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker


database_url = os.getenv("DATABASE_URL")

if not database_url:
    db_user = quote_plus(
        os.environ["DB_USER"]
    )
    db_password = quote_plus(
        os.environ["DB_PASSWORD"]
    )
    db_host = os.environ["DB_HOST"]
    db_port = os.getenv(
        "DB_PORT",
        "3306",
    )
    db_name = quote_plus(
        os.environ["DB_NAME"]
    )

    database_url = (
        f"mysql+pymysql://{db_user}:{db_password}"
        f"@{db_host}:{db_port}/{db_name}"
        "?charset=utf8mb4"
    )


engine_options: dict[str, object] = {
    "pool_pre_ping": True,
}

if database_url.startswith("sqlite:"):
    engine_options["connect_args"] = {
        "check_same_thread": False,
    }
else:
    engine_options["pool_recycle"] = 1800


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


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()