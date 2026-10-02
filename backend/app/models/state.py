from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


unsigned_integer = Integer().with_variant(
    mysql.INTEGER(unsigned=True),
    "mysql",
)


class State(Base):
    __tablename__ = "states"

    state_id: Mapped[int] = mapped_column(
        unsigned_integer,
        primary_key=True,
        autoincrement=True,
    )
    state_name: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        unique=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
