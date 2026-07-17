from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    """Body for POST /attendance/checkIn."""

    qr_token: str = Field(description="The qr_token associated with the User that is checking in")
    event_id: str = Field(description="The id for the event that we are checking in for")
    is_manual_check_in: bool = Field(
        default=False, description="A flag for if the user was scanned in or manually signed in"
    )
