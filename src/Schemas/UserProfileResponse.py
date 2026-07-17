from pydantic import BaseModel, Field


class UserProfileResponse(BaseModel):
    """Public profile for an active user from GET /accounts/userProfile/{uuid}."""

    first_name: str | None = Field(description="Given name; null if not set.")
    last_name: str | None = Field(description="Family name; null if not set.")
    email: str | None = Field(description="Primary email; null if not set.")
    phone_number: str | None = Field(description="Phone digits null if not set.")
    date_of_birth: str | None = Field(
        description="Birth date as `YYYY-MM-DD` string; empty string if not set."
    )
    zip_code: str | None = Field(description="Postal/ZIP code; null if not set.")
    address: str | None = Field(description="Street or mailing address line; null if not set.")
    race: str | None = Field(description="Human readable race/ethnicity label")
