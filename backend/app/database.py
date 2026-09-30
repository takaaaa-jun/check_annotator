import os
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


db_user = quote_plus(os.environ["DB_USER"])
db_password = quote_plus(os.environ["DB_PASSWORD"])
db_host = os.environ["DB_HOST"]
db_port = os.getenv("DB_PORT", "3306")
db_name = quote_plus(os.environ["DB_NAME"])

database_url = (
    f"mysql+pymysql://{db_user}:{db_password}"
    f"@{db_host}:{db_port}/{db_name}"
    "?charset=utf8mb4"
)

engine = create_engine(
    database_url,
    pool_pre_ping=True,
    pool_recycle=1800,
)

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