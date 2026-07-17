from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class EventRegistrationRequest(BaseModel):
    name: str = Field(description="The name of the event")
    description: str = Field(description="Description of the event")
    location: str = Field(description="Where the event is")
    type_id: int = Field(description="The type of event")
    start_datetime: datetime = Field(description="The date and time when the event starts")
    end_datetime: datetime = Field(description="The date and time when the event ends")

    @field_validator("start_datetime", "end_datetime", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)
