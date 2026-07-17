from datetime import datetime

from pydantic import BaseModel


class AttendeeResponse(BaseModel):
    attendance_id: str
    first_name: str | None
    last_name: str | None
    check_in_time: datetime

    model_config = {"from_attributes": True}
