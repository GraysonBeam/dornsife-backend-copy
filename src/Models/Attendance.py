import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.Models.Base import Base
from src.Models.User import User


class Attendance(Base):
    __tablename__ = "attendance"  # Lowercase is standard in Postgres

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    check_in_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    user_id: Mapped[str | None] = mapped_column(
        Text, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    event_instance_id: Mapped[str] = mapped_column(
        Text, ForeignKey("events.id", ondelete="CASCADE")
    )
    check_in_method_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("checkinmethodtypes.checkinid")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )

    user: Mapped["User | None"] = relationship("User", foreign_keys=[user_id])

    __table_args__ = (UniqueConstraint("user_id", "event_instance_id", name="uq_user_event"),)
