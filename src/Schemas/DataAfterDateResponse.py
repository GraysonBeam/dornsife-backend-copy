from pydantic import BaseModel, Field

from src.Schemas.AttendanceAnalyticsRecord import AttendanceAnalyticsRecord


class DataAfterDateResponse(BaseModel):
    """Response containing attendance analytics records after a specified date.

    Returns a list of attendance records with deidentified user and event data
    suitable for statistical analysis, ordered by event start time.
    """

    records: list[AttendanceAnalyticsRecord] = Field(
        default_factory=list,
        description="List of attendance records with analytics data, ordered by event start time",
    )
    total_count: int = Field(description="Total number of records returned")
