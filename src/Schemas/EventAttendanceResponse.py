from pydantic import BaseModel

from src.Schemas.AttendeeResponse import AttendeeResponse


class EventAttendanceResponse(BaseModel):
    event_id: str
    attendees: list[AttendeeResponse]
