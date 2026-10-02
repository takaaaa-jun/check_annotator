from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.group import Group
from app.models.state import State
from app.models.task import Task


@dataclass(frozen=True)
class StateCountRecord:
    state_id: int
    state_name: str
    count: int


@dataclass(frozen=True)
class GroupProgressRecord:
    group_id: int
    group_name: str
    image_id_min: int | None
    image_id_max: int | None
    total_count: int
    state_counts: list[StateCountRecord]


class GroupRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_progress_by_user_id(
        self,
        user_id: int,
    ) -> list[GroupProgressRecord]:
        groups = list(
            self.db.scalars(
                select(Group)
                .where(
                    Group.user_id == user_id,
                    Group.deleted_at.is_(None),
                )
                .order_by(Group.group_id)
            )
        )

        if not groups:
            return []

        states = list(
            self.db.scalars(
                select(State)
                .where(State.deleted_at.is_(None))
                .order_by(State.state_id)
            )
        )
        group_ids = [group.group_id for group in groups]

        summaries = self.db.execute(
            select(
                Task.group_id,
                func.min(Task.image_id),
                func.max(Task.image_id),
                func.count(Task.task_id),
            )
            .join(State, State.state_id == Task.state_id)
            .where(
                Task.group_id.in_(group_ids),
                Task.deleted_at.is_(None),
                State.deleted_at.is_(None),
            )
            .group_by(Task.group_id)
        ).all()
        summary_by_group = {
            row[0]: (row[1], row[2], row[3])
            for row in summaries
        }

        counts = self.db.execute(
            select(
                Task.group_id,
                Task.state_id,
                func.count(Task.task_id),
            )
            .join(State, State.state_id == Task.state_id)
            .where(
                Task.group_id.in_(group_ids),
                Task.deleted_at.is_(None),
                State.deleted_at.is_(None),
            )
            .group_by(Task.group_id, Task.state_id)
        ).all()
        count_by_group_and_state = {
            (row[0], row[1]): row[2]
            for row in counts
        }

        records: list[GroupProgressRecord] = []
        for group in groups:
            image_id_min, image_id_max, total_count = summary_by_group.get(
                group.group_id,
                (None, None, 0),
            )
            records.append(
                GroupProgressRecord(
                    group_id=group.group_id,
                    group_name=group.group_name,
                    image_id_min=image_id_min,
                    image_id_max=image_id_max,
                    total_count=total_count,
                    state_counts=[
                        StateCountRecord(
                            state_id=state.state_id,
                            state_name=state.state_name,
                            count=count_by_group_and_state.get(
                                (group.group_id, state.state_id),
                                0,
                            ),
                        )
                        for state in states
                    ],
                )
            )

        return records

    def find_active_by_id(self, group_id: int) -> Group | None:
        return self.db.scalar(
            select(Group).where(
                Group.group_id == group_id,
                Group.deleted_at.is_(None),
            )
        )
