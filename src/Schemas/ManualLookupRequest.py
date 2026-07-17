from typing import Self

from pydantic import BaseModel, Field, model_validator

from src.Utils.Validators import ValidationError, Validator


class ManualLookupRequest(BaseModel):
    """Request body for manual user lookup."""

    email: str | None = Field(default=None, description="Email address to lookup")
    phone_number: str | None = Field(default=None, description="Phone number to lookup")

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
