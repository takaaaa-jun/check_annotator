from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


unsigned_integer = Integer().with_variant(
    mysql.INTEGER(unsigned=True),
    "mysql",
)


class Role(Base):
    __tablename__ = "roles"

    role_id: Mapped[int] = mapped_column(
        unsigned_integer,
        primary_key=True,
        autoincrement=True,
    )

    role_name: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    users: Mapped[list["User"]] = relationship(
        back_populates="role",
    )