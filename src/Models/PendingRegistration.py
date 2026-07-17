import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Models.Base import Base
from src.Models.User import User


class PendingRegistration(Base):
    __tablename__ = "pendingregistration"

    ID: Mapped[str] = mapped_column(
        "id",
        Text,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        server_default=text("gen_random_uuid()"),
    )
    USER_ID: Mapped[str] = mapped_column(
        "user_id", Text, ForeignKey("users.id", ondelete="CASCADE", onupdate="CASCADE")
    )
    CREATED_AT: Mapped[datetime] = mapped_column(
        "created_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    UPDATED_AT: Mapped[datetime] = mapped_column(
        "updated_at", DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    NEW_EMAIL: Mapped[str | None] = mapped_column("new_email", Text)
    NEW_PHONE_NUMBER: Mapped[str | None] = mapped_column("new_phone_number", Text)

    user: Mapped[User] = relationship("User")
