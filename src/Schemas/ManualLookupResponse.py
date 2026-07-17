from pydantic import BaseModel, Field


class ManualLookupResponse(BaseModel):
    """Response model for manual user lookup."""

    first_name: str | None = Field(description="First name of the user")
    last_name: str | None = Field(description="Last name of the user")
    email: str | None = Field(description="Email address of the user")
    phone_number: str | None = Field(description="Phone number of the user")
    date_of_birth: str | None = Field(description="Date of birth in YYYY-MM-DD format")
    zip_code: str | None = Field(description="Zip code")
    address: str | None = Field(description="Address")
    race: str | None = Field(description="Race description")
    qr_token: str | None = Field(description="QR token for the user")
