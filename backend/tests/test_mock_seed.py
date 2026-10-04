from sqlalchemy import (
    create_engine,
    func,
    select,
)
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.security import (
    verify_password,
)
from app.models.comment import Comment
from app.models.group import Group
from app.models.role import Role
from app.models.state import State
from app.models.task import Task
from app.models.user import User
from app.mock.seed import (
    prepare_mock_database,
)


def create_mock_engine():
    return create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )


def test_prepare_mock_database_seeds_json_data() -> None:
    mock_engine = create_mock_engine()

    assert (
        prepare_mock_database(
            mock_engine
        )
        is True
    )

    with Session(mock_engine) as db:
        assert db.scalar(
            select(
                func.count(Role.role_id)
            )
        ) == 2

        assert db.scalar(
            select(
                func.count(User.user_id)
            )
        ) == 3

        assert db.scalar(
            select(
                func.count(State.state_id)
            )
        ) == 4

        assert db.scalar(
            select(
                func.count(Group.group_id)
            )
        ) == 2

        assert db.scalar(
            select(
                func.count(Task.task_id)
            )
        ) == 12

        assert db.scalar(
            select(
                func.count(
                    Comment.comment_id
                )
            )
        ) == 2

        user = db.scalar(
            select(User).where(
                User.user_name
                == "takahashi"
            )
        )

        assert user is not None

        assert verify_password(
            "test1",
            user.password_hash,
        )


def test_prepare_mock_database_is_idempotent() -> None:
    mock_engine = create_mock_engine()

    assert (
        prepare_mock_database(
            mock_engine
        )
        is True
    )

    assert (
        prepare_mock_database(
            mock_engine
        )
        is False
    )

    with Session(mock_engine) as db:
        assert db.scalar(
            select(
                func.count(User.user_id)
            )
        ) == 3

        assert db.scalar(
            select(
                func.count(Task.task_id)
            )
        ) == 12


def test_prepare_mock_database_can_reset_data() -> None:
    mock_engine = create_mock_engine()

    prepare_mock_database(
        mock_engine
    )

    with Session(mock_engine) as db:
        task = db.get(Task, 1)

        assert task is not None

        task.state_id = 2
        db.commit()

    assert (
        prepare_mock_database(
            mock_engine,
            reset=True,
        )
        is True
    )

    with Session(mock_engine) as db:
        task = db.get(Task, 1)

        assert task is not None
        assert task.state_id == 1