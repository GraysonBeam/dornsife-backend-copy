from pydantic import BaseModel, Field


class ActivateAccountRequest(BaseModel):
    """Body for POST /accounts/activate."""

    id: str = Field(description="Pending registration UUID")
    verification_code: str = Field(description="Code received from email/SMS")
    verification_type: str = Field(description="Type of verification between email/SMS")
