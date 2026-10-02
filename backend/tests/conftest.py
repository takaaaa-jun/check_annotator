import os
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DB_USER", "test")
os.environ.setdefault("DB_PASSWORD", "test")
os.environ.setdefault("DB_HOST", "localhost")
os.environ.setdefault("DB_NAME", "test")
os.environ.setdefault(
    "AUTH_SECRET_KEY",
    "test-secret-key-for-login-tests-2026",
)

from app.core.security import password_hash  # noqa: E402
from app.database import get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.role import Role  # noqa: E402
from app.models.user import User  # noqa: E402


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    now = datetime.now(UTC).replace(tzinfo=None)
    with TestingSessionLocal() as db:
        role = Role(
            role_name="worker",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        db.add(role)
        db.flush()
        db.add(
            User(
                user_name="takahashi",
                password_hash=password_hash.hash("test1"),
                role_id=role.role_id,
                login_at=None,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
        )
        db.add(
            User(
                user_name="deleted-user",
                password_hash=password_hash.hash("test1"),
                role_id=role.role_id,
                login_at=None,
                created_at=now,
                updated_at=now,
                deleted_at=now,
            )
        )
        db.commit()

    yield


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    with TestingSessionLocal() as db:
        yield db
