from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


unsigned_integer = Integer().with_variant(
    mysql.INTEGER(unsigned=True),
    "mysql",
)


class Group(Base):
    __tablename__ = "groups"

    group_id: Mapped[int] = mapped_column(
        unsigned_integer,
        primary_key=True,
        autoincrement=True,
    )
    group_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )
    user_id: Mapped[int | None] = mapped_column(
        unsigned_integer,
        ForeignKey(
            "users.user_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
