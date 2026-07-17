from pydantic import BaseModel, Field


class EventRaceBucketItem(BaseModel):
    """One race/ethnicity group in event attendance demographics."""

    race: str = Field(description="Race/ethnicity description from race lookup")
    race_count: int = Field(description="Number of attendees in this race category")


class GetEventBucketRaceResponse(BaseModel):
    """Race attendance buckets for GET /attendance/event-race-bucket."""

    buckets: list[EventRaceBucketItem] = Field(
        default_factory=list,
        description="Race categories and attendee counts for the event, ordered by count desc",
    )
