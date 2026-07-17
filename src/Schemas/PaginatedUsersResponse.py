from pydantic import BaseModel, Field


class PaginatedUsersResponse(BaseModel):
    """One user row returned from GET /accounts/users/paginated."""

    first_name: str | None = Field(description="Given name; null if not set.")
    last_name: str | None = Field(description="Family name; null if not set.")
    email: str | None = Field(description="Primary email; null if not set.")
    phone_number: str | None = Field(description="Phone number; null if not set.")
    date_of_birth: str | None = Field(description="Birth date as YYYY-MM-DD; null if not set.")
    zip_code: str | None = Field(description="Postal/ZIP code; null if not set.")
    address: str | None = Field(description="Street or mailing address; null if not set.")
    race_description: str | None = Field(description="Human-readable race/ethnicity label.")
    is_active: bool = Field(description="Whether the account is active.")
    parent_first_name: str | None = Field(
        description="Parent's given name; null if top-level account."
    )
    parent_last_name: str | None = Field(
        description="Parent's family name; null if top-level account."
    )
