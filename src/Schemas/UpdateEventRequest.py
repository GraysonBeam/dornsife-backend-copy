from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class UpdateEventRequest(BaseModel):
    name: str | None = Field(default=None, description="Name of the event")
    description: str | None = Field(default=None, description="Description of the event")
    location: str | None = Field(default=None, description="Location where the event is held")
    type_id: int | None = Field(
        default=None, description="Integer ID corresponding to the event type"
    )
    start_datetime: datetime | None = Field(
        default=None, description="Event start datetime in ISO 8601 format"
    )
    end_datetime: datetime | None = Field(
        default=None, description="Event end datetime in ISO 8601 format"
    )

    @field_validator("start_datetime", "end_datetime", mode="after")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v.astimezone(UTC)
