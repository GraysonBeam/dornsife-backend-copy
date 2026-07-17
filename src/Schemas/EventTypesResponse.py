from pydantic import BaseModel, Field


class EventTypeItem(BaseModel):
    """One event type choice for registration/admin UI."""

    key: str = Field(description="Label/name of the event type")
    id: int = Field(description="Numeric event type id")


class EventTypesResponse(BaseModel):
    """Event type lookup list from GET /events/eventTypes."""

    event_types: list[EventTypeItem] = Field(description="Key and id for each event type")
