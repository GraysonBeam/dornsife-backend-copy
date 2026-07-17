from enum import Enum

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.Models.Base import Base


class CheckInMethodsEnum(Enum):
    QR_CODE = 1
    MANUAL = 2


class CheckInMethodType(Base):
    __tablename__ = "checkinmethodtypes"

    checkinid: Mapped[int] = mapped_column(
        "checkinid", Integer, primary_key=True, autoincrement=True
    )
    methodtype: Mapped[str] = mapped_column("methodtype", String, nullable=False, unique=True)
