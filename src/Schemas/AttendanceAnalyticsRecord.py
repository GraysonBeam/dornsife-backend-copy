from datetime import datetime

from pydantic import BaseModel, Field


class AttendanceAnalyticsRecord(BaseModel):
    """A single attendance record with related event and user data for analytics.

    This record contains anonymized user data suitable for statistical analysis,
    excluding sensitive PII like date of birth, name, email, and phone number.
    """

    event_name: str = Field(description="Name of the event")
    event_start_time: datetime = Field(description="Event start datetime")
    event_end_time: datetime = Field(description="Event end datetime")
    event_location: str | None = Field(description="Event location")
    event_type: str = Field(description="Type of the event")
    user_age: int | None = Field(description="Age of the linked user in years")
    user_zip_code: str | None = Field(description="Zip code of the linked user")
    has_parent: bool = Field(
        description="Whether the linked user has a parent (is parent_id not null)"
    )
    check_in_method: str = Field(description="Method used for check-in (e.g., QR code, Manual)")
    user_race: str | None = Field(description="Race/Ethnicity of the linked user")
