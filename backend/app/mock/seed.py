import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.security import password_hash
from app.db.base import Base
from app.models.comment import Comment
from app.models.group import Group
from app.models.role import Role
from app.models.state import State
from app.models.task import Task
from app.models.user import User


DEFAULT_DATA_DIRECTORY = (
    Path(__file__).parent / "data"
)

DEFAULT_TIMESTAMP = datetime(
    2026,
    10,
    4,
    tzinfo=UTC,
).replace(tzinfo=None)


def _read_json(
    data_directory: Path,
    file_name: str,
) -> dict[str, Any]:
    file_path = data_directory / file_name

    with file_path.open(
        encoding="utf-8",
    ) as file:
        value = json.load(file)

    if not isinstance(value, dict):
        raise ValueError(
            f"{file_name} must contain "
            "a JSON object"
        )

    return value


def _parse_datetime(
    value: str | None,
) -> datetime | None:
    if value is None:
        return None

    parsed = datetime.fromisoformat(
        value.replace(
            "Z",
            "+00:00",
        )
    )

    if parsed.tzinfo is None:
        return parsed

    return parsed.astimezone(
        UTC
    ).replace(tzinfo=None)


def _validate_progress_data(
    groups_data: dict[str, Any],
    tasks_data: dict[str, Any],
) -> None:
    tasks_by_group = {
        item["group"]["group_id"]:
            item["tasks"]
        for item in tasks_data["groups"]
    }

    for user_entry in groups_data["users"]:
        for group in user_entry["groups"]:
            group_id = group["group_id"]

            tasks = tasks_by_group.get(
                group_id
            )

            if tasks is None:
                raise ValueError(
                    "Tasks are missing for "
                    f"group {group_id}"
                )

            if (
                len(tasks)
                != group["total_count"]
            ):
                raise ValueError(
                    "Task total does not match "
                    f"group {group_id}"
                )

            for state_count in (
                group["state_counts"]
            ):
                actual_count = sum(
                    task["state_id"]
                    == state_count["state_id"]
                    for task in tasks
                )

                if (
                    actual_count
                    != state_count["count"]
                ):
                    raise ValueError(
                        "State count does not "
                        "match "
                        f"group {group_id}, "
                        "state "
                        f"{state_count['state_id']}"
                    )


def _seed_session(
    db: Session,
    data_directory: Path,
) -> None:
    auth_data = _read_json(
        data_directory,
        "auth.json",
    )

    groups_data = _read_json(
        data_directory,
        "groups.json",
    )

    tasks_data = _read_json(
        data_directory,
        "group-tasks.json",
    )

    comments_data = _read_json(
        data_directory,
        "comments.json",
    )

    _validate_progress_data(
        groups_data,
        tasks_data,
    )

    accounts = auth_data["accounts"]

    roles_by_id = {
        account["current_user"]["role_id"]:
            account["current_user"][
                "role_name"
            ]
        for account in accounts
    }

    db.add_all(
        [
            Role(
                role_id=role_id,
                role_name=role_name,
                created_at=(
                    DEFAULT_TIMESTAMP
                ),
                updated_at=(
                    DEFAULT_TIMESTAMP
                ),
                deleted_at=None,
            )
            for role_id, role_name
            in sorted(
                roles_by_id.items()
            )
        ]
    )

    db.flush()

    db.add_all(
        [
            User(
                user_id=account[
                    "current_user"
                ]["user_id"],
                user_name=account[
                    "credentials"
                ]["user_name"],
                password_hash=(
                    password_hash.hash(
                        account[
                            "credentials"
                        ]["password"]
                    )
                ),
                role_id=account[
                    "current_user"
                ]["role_id"],
                login_at=_parse_datetime(
                    account[
                        "current_user"
                    ]["login_at"]
                ),
                created_at=(
                    DEFAULT_TIMESTAMP
                ),
                updated_at=(
                    DEFAULT_TIMESTAMP
                ),
                deleted_at=None,
            )
            for account in accounts
        ]
    )

    db.flush()

    state_names: dict[int, str] = {}

    for user_entry in groups_data["users"]:
        for group in user_entry["groups"]:
            for state_count in (
                group["state_counts"]
            ):
                state_names[
                    state_count["state_id"]
                ] = state_count[
                    "state_name"
                ]

    db.add_all(
        [
            State(
                state_id=state_id,
                state_name=state_name,
                created_at=(
                    DEFAULT_TIMESTAMP
                ),
                updated_at=(
                    DEFAULT_TIMESTAMP
                ),
                deleted_at=None,
            )
            for state_id, state_name
            in sorted(
                state_names.items()
            )
        ]
    )

    db.flush()

    db.add_all(
        [
            Group(
                group_id=group["group_id"],
                group_name=group[
                    "group_name"
                ],
                user_id=user_entry[
                    "user"
                ]["user_id"],
                created_at=(
                    DEFAULT_TIMESTAMP
                ),
                updated_at=(
                    DEFAULT_TIMESTAMP
                ),
                deleted_at=None,
            )
            for user_entry
            in groups_data["users"]
            for group
            in user_entry["groups"]
        ]
    )

    db.flush()

    task_entries = [
        (
            group_entry["group"][
                "group_id"
            ],
            task,
        )
        for group_entry
        in tasks_data["groups"]
        for task in group_entry["tasks"]
    ]

    db.add_all(
        [
            Task(
                task_id=task["task_id"],
                group_id=group_id,
                image_id=task["image_id"],
                state_id=task["state_id"],
                created_at=(
                    _parse_datetime(
                        task["updated_at"]
                    )
                    or DEFAULT_TIMESTAMP
                ),
                updated_at=(
                    _parse_datetime(
                        task["updated_at"]
                    )
                    or DEFAULT_TIMESTAMP
                ),
                deleted_at=None,
            )
            for group_id, task
            in task_entries
        ]
    )

    db.flush()

    db.add_all(
        [
            Comment(
                comment_id=comment[
                    "comment_id"
                ],
                task_id=task_entry[
                    "task_id"
                ],
                user_id=comment[
                    "user_id"
                ],
                parent_id=comment[
                    "parent_id"
                ],
                content=comment[
                    "content"
                ],
                created_at=(
                    _parse_datetime(
                        comment["created_at"]
                    )
                    or DEFAULT_TIMESTAMP
                ),
                updated_at=(
                    _parse_datetime(
                        comment["updated_at"]
                    )
                    or DEFAULT_TIMESTAMP
                ),
                deleted_at=None,
            )
            for task_entry
            in comments_data["tasks"]
            for comment
            in task_entry["comments"]
        ]
    )

    db.commit()


def prepare_mock_database(
    target_engine: Engine,
    *,
    reset: bool = False,
    data_directory: Path = (
        DEFAULT_DATA_DIRECTORY
    ),
) -> bool:
    if reset:
        Base.metadata.drop_all(
            bind=target_engine
        )

    Base.metadata.create_all(
        bind=target_engine
    )

    with Session(target_engine) as db:
        user_count = db.scalar(
            select(
                func.count(User.user_id)
            )
        ) or 0

        if user_count > 0:
            return False

        try:
            _seed_session(
                db,
                data_directory,
            )
        except Exception:
            db.rollback()
            raise

    return True