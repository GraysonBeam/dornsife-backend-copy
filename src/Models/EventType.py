from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.Models.Base import Base


class EventType(Base):
    __tablename__ = "eventtypes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
