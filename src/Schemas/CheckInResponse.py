from datetime import datetime

from pydantic import BaseModel, Field


class CheckInResponse(BaseModel):
    """Returned after a successful POST /attendance/checkIn."""

    attendance_id: str = Field(description="The id for the created attendance record")
    timestamp: datetime = Field(
        description="The datetime timestamp of when the check in was completed"
    )
