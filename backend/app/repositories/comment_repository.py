from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.comment import Comment


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
