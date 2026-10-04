import os
from collections.abc import Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool


os.environ["DB_USER"] = "test"
os.environ["DB_PASSWORD"] = "test"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_NAME"] = "test"
os.environ["APP_DATA_MODE"] = "database"
os.environ["AUTH_SECRET_KEY"] = (
    "test-secret-key-for-login-tests-2026"
)

from app.core.security import password_hash  # noqa: E402
from app.database import get_db  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import app  # noqa: E402
from app.models.comment import Comment  # noqa: E402, F401
from app.models.role import Role  # noqa: E402
from app.models.group import Group  # noqa: E402
from app.models.state import State  # noqa: E402
from app.models.task import Task  # noqa: E402
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
        admin_role = Role(
            role_name="admin",
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        db.add(admin_role)
        db.flush()
        no_groups_user = User(
            user_name="no-groups-user",
            password_hash=password_hash.hash("test1"),
            role_id=role.role_id,
            login_at=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        admin_user = User(
            user_name="admin-user",
            password_hash=password_hash.hash("test1"),
            role_id=admin_role.role_id,
            login_at=None,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        db.add_all([no_groups_user, admin_user])
        db.flush()

        states = [
            State(
                state_name=state_name,
                created_at=now,
                updated_at=now,
                deleted_at=None,
            )
            for state_name in [
                "未着手",
                "完了",
                "付与予定ラベル",
                "コメント",
            ]
        ]
        deleted_state = State(
            state_name="削除済み状態",
            created_at=now,
            updated_at=now,
            deleted_at=now,
        )
        db.add_all([*states, deleted_state])
        db.flush()

        active_group = Group(
            group_name="グループ1",
            user_id=1,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        empty_group = Group(
            group_name="空グループ",
            user_id=1,
            created_at=now,
            updated_at=now,
            deleted_at=None,
        )
        deleted_group = Group(
            group_name="削除済みグループ",
            user_id=1,
            created_at=now,
            updated_at=now,
            deleted_at=now,
        )
        db.add_all([active_group, empty_group, deleted_group])
        db.flush()

        db.add_all(
            [
                Task(
                    group_id=active_group.group_id,
                    image_id=image_id,
                    state_id=state_id,
                    created_at=now,
                    updated_at=now,
                    deleted_at=deleted_at,
                )
                for image_id, state_id, deleted_at in [
                    (10, states[0].state_id, None),
                    (11, states[0].state_id, None),
                    (20, states[1].state_id, None),
                    (30, states[1].state_id, now),
                    (40, deleted_state.state_id, None),
                ]
            ]
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
