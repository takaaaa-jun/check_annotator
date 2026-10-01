from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


unsigned_integer = Integer().with_variant(
    mysql.INTEGER(unsigned=True),
    "mysql",
)


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        unsigned_integer,
        primary_key=True,
        autoincrement=True,
    )

    user_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
    )

    password_hash: Mapped[str] = mapped_column(
        "password",
        String(255),
        nullable=False,
    )

    role_id: Mapped[int] = mapped_column(
        unsigned_integer,
        ForeignKey(
            "roles.role_id",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
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

    role: Mapped["Role"] = relationship(
        back_populates="users",
    )