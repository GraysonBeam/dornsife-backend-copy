from pydantic import BaseModel, Field


class EventAgeBucketItem(BaseModel):
    """One age-range group in event attendance demographics."""

    age_bucket: str = Field(description="Age range label (e.g. 18-24, 45+)")
    attendee_count: int = Field(description="Number of attendees in this age range")


class GetEventBucketAgeResponse(BaseModel):
    """Age attendance buckets for GET /attendance/event-age-bucket."""

    buckets: list[EventAgeBucketItem] = Field(
        default_factory=list,
        description="Age ranges and attendee counts for the event, ordered by age bucket",
    )
