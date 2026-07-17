from pydantic import BaseModel, Field


class UserRegistrationResponse(BaseModel):
    """Returned after POST /userRegistration/user when registration is accepted."""

    status: str = Field(description="Outcome label")
    pending_registration_id: str = Field(description="UUID of the `pendingregistration` row")
