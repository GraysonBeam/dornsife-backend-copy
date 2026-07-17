from pydantic import BaseModel, Field


class UpdateUserProfileResponse(BaseModel):
    message: str = Field(description="Human-readable summary of the update result")
    pending_registration_id: str | None = Field(
        default=None,
        description="ID of the pending registration created when\
                an email change is requested — null if no email change was made",
    )
    first_name: str | None = Field(default=None, description="User's updated first name")
    last_name: str | None = Field(default=None, description="User's updated last name")
    email: str | None = Field(
        default=None,
        description="User's current email — will not reflect\
                the new email until verification is complete",
    )
    phone_number: str | None = Field(default=None, description="User's updated phone number")
    date_of_birth: str | None = Field(
        default=None, description="User's date of birth in format YYYY-MM-DD"
    )
    zip_code: str | None = Field(default=None, description="User's updated zip code")
    address: str | None = Field(default=None, description="User's updated street address")
    race: str | None = Field(
        default=None, description="Human-readable race description resolved from race_id"
    )
