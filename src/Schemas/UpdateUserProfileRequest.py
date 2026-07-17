from typing import Self

from pydantic import BaseModel, Field, model_validator

from src.Utils.Validators import ValidationError, Validator


class UpdateUserProfileRequest(BaseModel):
    first_name: str | None = Field(default=None, description="User's first name")
    last_name: str | None = Field(default=None, description="User's last name")
    email: str | None = Field(
        default=None,
        description="New email address — will trigger a verification email before being applied",
    )
    phone_number: str | None = Field(
        default=None, description="User's phone number in format XXX-XXX-XXXX"
    )
    date_of_birth: str | None = Field(
        default=None, description="User's date of birth in format YYYY-MM-DD"
    )
    zip_code: str | None = Field(default=None, description="User's 5-digit zip code")
    address: str | None = Field(default=None, description="User's street address")
    race_id: int | None = Field(
        default=None,
        description="Integer ID corresponding to the user's race from the race lookup table",
    )

    @model_validator(mode="after")
    def normalize_contact_fields(self) -> Self:
        try:
            self.email, self.phone_number = Validator.validate_contact_fields(
                self.email,
                self.phone_number,
                require_one=False,
            )
        except ValidationError as e:
            raise ValueError(str(e)) from e

        return self
