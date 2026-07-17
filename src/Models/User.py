import uuid
from datetime import date, datetime

from sqlalchemy import ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.Models.Base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    email: Mapped[str | None] = mapped_column(Text)
    phone_number: Mapped[str | None] = mapped_column(Text)
    date_of_birth: Mapped[date | None]
    zip_code: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    race_id: Mapped[int] = mapped_column(ForeignKey("race_lookup.race_id"))
    qr_token: Mapped[str | None] = mapped_column(Text, unique=True)
    is_active: Mapped[bool] = mapped_column(default=True)
    parent_id: Mapped[str | None] = mapped_column(Text, ForeignKey("users.id"))

    created_at: Mapped[datetime | None]
    updated_at: Mapped[datetime | None]


class RaceLookup(Base):
    __tablename__ = "race_lookup"

    race_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    description: Mapped[str] = mapped_column(Text)
