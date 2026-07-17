from datetime import datetime

from pydantic import BaseModel, Field


class ActiveEvent(BaseModel):
    """One event returned from GET /events/activeEvents."""

    id: str = Field(description="Event id (UUID string).")
    name: str = Field(description="Display name shown to users.")
    start_datetime: datetime = Field(description="When the event starts")
    end_datetime: datetime = Field(description="When the event ends")


class GetActiveEventsResponse(BaseModel):
    """Wrapper for the active-events list (response body shape)."""

    events: list[ActiveEvent] = Field(
        default_factory=list,
        description="Currently active events, ordered by start_datetime ascending",
    )
