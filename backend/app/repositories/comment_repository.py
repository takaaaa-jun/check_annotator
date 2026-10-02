from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.user import User


@dataclass(frozen=True)
class CommentRecord:
    comment_id: int
    user_id: int
    user_name: str
    parent_id: int | None
    content: str
    created_at: datetime
    updated_at: datetime


class CommentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_active_by_id(self, comment_id: int) -> Comment | None:
        return self.db.scalar(
            select(Comment).where(
                Comment.comment_id == comment_id,
                Comment.deleted_at.is_(None),
            )
        )

    def find_page(
        self,
        task_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[CommentRecord], int]:
        filters = [
            Comment.task_id == task_id,
            Comment.deleted_at.is_(None),
        ]
        total = self.db.scalar(
            select(func.count(Comment.comment_id)).where(*filters)
        ) or 0
        rows = self.db.execute(
            select(Comment, User.user_name)
            .join(User, User.user_id == Comment.user_id)
            .where(*filters)
            .order_by(Comment.created_at, Comment.comment_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return (
            [
                CommentRecord(
                    comment_id=comment.comment_id,
                    user_id=comment.user_id,
                    user_name=user_name,
                    parent_id=comment.parent_id,
                    content=comment.content,
                    created_at=comment.created_at,
                    updated_at=comment.updated_at,
                )
                for comment, user_name in rows
            ],
            total,
        )

    def create(
        self,
        task_id: int,
        user_id: int,
        parent_id: int | None,
        content: str,
        created_at: datetime,
    ) -> Comment:
        comment = Comment(
            task_id=task_id,
            user_id=user_id,
            parent_id=parent_id,
            content=content,
            created_at=created_at,
            updated_at=created_at,
            deleted_at=None,
        )
        self.db.add(comment)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(comment)
        return comment
