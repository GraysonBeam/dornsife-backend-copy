from datetime import datetime

from pydantic import BaseModel, Field


class EventItem(BaseModel):
    id: str = Field(description="Event ID")
    name: str = Field(description="Event name")
    description: str | None = Field(description="Event description")
    start_datetime: datetime = Field(description="Event start datetime")
    end_datetime: datetime = Field(description="Event end datetime")
    location: str | None = Field(description="Event location")
    type_id: int = Field(description="Event type ID")


class GetEventsResponse(BaseModel):
    events: list[EventItem] = Field(description="List of events")
