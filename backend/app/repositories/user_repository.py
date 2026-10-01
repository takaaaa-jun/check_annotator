from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def find_active_by_user_name(
        self,
        user_name: str,
    ) -> User | None:
        statement = (
            select(User)
            .options(joinedload(User.role))
            .where(
                User.user_name == user_name,
                User.deleted_at.is_(None),
            )
        )

        return self.db.scalar(statement)

    def update_login_at(
        self,
        user: User,
        login_at: datetime,
    ) -> None:
        user.login_at = login_at

        self.db.commit()
        self.db.refresh(user)