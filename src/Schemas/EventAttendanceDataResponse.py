from pydantic import BaseModel, Field

from src.Schemas.AttendanceAnalyticsRecord import AttendanceAnalyticsRecord


class EventAttendanceDataResponse(BaseModel):
    """Response containing attendance analytics records for a specific event.

    Returns a list of attendance records with deidentified user and event data
    suitable for statistical analysis, ordered by check-in time.
    """

    records: list[AttendanceAnalyticsRecord] = Field(
        default_factory=list,
        description="List of attendance records with analytics data, ordered by check-in time",
    )
    total_count: int = Field(description="Total number of records returned")
