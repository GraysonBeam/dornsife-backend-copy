from typing import Self

from pydantic import BaseModel, Field, model_validator

from src.Utils.Validators import ValidationError, Validator


class UserRegistrationRequest(BaseModel):
    """Body for POST /userRegistration/user. Creates an inactive user and a pending registration."""

    first_name: str = Field(description="Given name")
    last_name: str = Field(description="Family name")
    email: str | None = Field(description="Contact email", default=None)
    phone_number: str | None = Field(
        default=None,
        description=(
            "Phone number, must be in E.164 format following "
            "+[Country Code][Subscriber Number] limited to 15 digits max"
        ),
    )
    date_of_birth: str = Field(description="`YYYY-MM-DD`. Must not be in the future")
    zip_code: str = Field(description="US-style ZIP: `12345` or `12345-6789` when provided.")
    address: str = Field(description="Street or mailing address line.")
    race_id: int = Field(description="Ethnicity/race lookup id")

    @model_validator(mode="after")
    def validate_and_normalize(self) -> Self:
        try:
            self.email, self.phone_number = Validator.validate_contact_fields(
                self.email,
                self.phone_number,
                require_one=True,
            )
        except ValidationError as e:
            raise ValueError(str(e)) from e

        return self
