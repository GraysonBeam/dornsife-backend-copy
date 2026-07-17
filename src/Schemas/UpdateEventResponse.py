from datetime import datetime

from pydantic import BaseModel, Field


class UpdateEventResponse(BaseModel):
    id: str = Field(description="Unique identifier of the updated event")
    name: str = Field(description="Name of the event")
    description: str = Field(description="Description of the event")
    location: str = Field(description="Location where the event is held")
    type_id: int = Field(description="Integer ID corresponding to the event type")
    start_datetime: datetime = Field(description="Event start datetime")
    end_datetime: datetime = Field(description="Event end datetime")
