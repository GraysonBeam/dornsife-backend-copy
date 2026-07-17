from pydantic import BaseModel, Field


class EventZipBucketItem(BaseModel):
    """One zip-code group in event attendance demographics."""

    zip_code: str = Field(description="Attendee zip code")
    zip_code_count: int = Field(description="Number of attendees from this zip code")


class GetEventBucketZipResponse(BaseModel):
    """Zip-code attendance buckets for GET /attendance/event-zip-bucket."""

    buckets: list[EventZipBucketItem] = Field(
        default_factory=list,
        description="Zip codes and attendee counts for the event, ordered by count descending",
    )
