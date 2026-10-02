from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.state import State
from app.models.task import Task


@dataclass(frozen=True)
class TaskRecord:
    task_id: int
    image_id: int
    state_id: int
    state_name: str
    updated_at: datetime


class TaskRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def state_exists(self, state_id: int) -> bool:
        return self.db.scalar(
            select(func.count(State.state_id)).where(
                State.state_id == state_id,
                State.deleted_at.is_(None),
            )
        ) > 0

    def find_active_with_state(self, task_id: int) -> tuple[Task, str] | None:
        row = self.db.execute(
            select(Task, State.state_name)
            .join(State, State.state_id == Task.state_id)
            .where(
                Task.task_id == task_id,
                Task.deleted_at.is_(None),
                State.deleted_at.is_(None),
            )
        ).one_or_none()
        return None if row is None else (row[0], row[1])

    def update_state(
        self,
        task: Task,
        state_id: int,
        updated_at: datetime,
    ) -> str:
        state_name = self.db.scalar(
            select(State.state_name).where(
                State.state_id == state_id,
                State.deleted_at.is_(None),
            )
        )
        if state_name is None:
            raise ValueError("state not found")
        task.state_id = state_id
        task.updated_at = updated_at
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(task)
        return state_name

    def find_page(
        self,
        group_id: int,
        state_id: int | None,
        page: int,
        page_size: int,
    ) -> tuple[list[TaskRecord], int]:
        filters = [
            Task.group_id == group_id,
            Task.deleted_at.is_(None),
            State.deleted_at.is_(None),
        ]
        if state_id is not None:
            filters.append(Task.state_id == state_id)

        total = self.db.scalar(
            select(func.count(Task.task_id))
            .join(State, State.state_id == Task.state_id)
            .where(*filters)
        ) or 0
        rows = self.db.execute(
            select(Task, State.state_name)
            .join(State, State.state_id == Task.state_id)
            .where(*filters)
            .order_by(Task.image_id, Task.task_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return (
            [
                TaskRecord(
                    task_id=task.task_id,
                    image_id=task.image_id,
                    state_id=task.state_id,
                    state_name=state_name,
                    updated_at=task.updated_at,
                )
                for task, state_name in rows
            ],
            total,
        )
