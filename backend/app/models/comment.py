from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


unsigned_integer = Integer().with_variant(
    mysql.INTEGER(unsigned=True),
    "mysql",
)


class Comment(Base):
    __tablename__ = "comments"

    comment_id: Mapped[int] = mapped_column(
        unsigned_integer,
        primary_key=True,
        autoincrement=True,
    )
    task_id: Mapped[int] = mapped_column(
        unsigned_integer,
        ForeignKey("tasks.task_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        unsigned_integer,
        ForeignKey("users.user_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    parent_id: Mapped[int | None] = mapped_column(
        unsigned_integer,
        ForeignKey("comments.comment_id", onupdate="CASCADE", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
