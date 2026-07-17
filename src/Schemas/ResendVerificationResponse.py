from pydantic import BaseModel, Field


class ResendVerificationResponse(BaseModel):
    """Returned after POST /userRegistration/resend."""

    status: str = Field(description="Outcome label")
