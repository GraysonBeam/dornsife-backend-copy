from pydantic import BaseModel, Field


class ResendVerificationRequest(BaseModel):
    """Body for POST /userRegistration/resend."""

    pending_registration_id: str = Field(description="UUID of the pending registration row")
    verification_type: str = Field(
        description="Specify whether to resend verification for email or sms"
    )
