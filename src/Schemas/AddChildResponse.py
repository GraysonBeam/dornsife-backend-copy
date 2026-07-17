from pydantic import BaseModel, Field


class AddChildResponse(BaseModel):
    id: str = Field(..., description="UUID of the newly created child account")
    first_name: str | None = Field(None, description="Child's first name")
    last_name: str | None = Field(None, description="Child's last name")
    email: str | None = Field(None, description="Child's email address")
    phone_number: str | None = Field(None, description="Child's phone number")
    date_of_birth: str | None = Field(None, description="Child's date of birth")
    zip_code: str | None = Field(None, description="Child's zip code")
    address: str | None = Field(None, description="Child's address")
    race_id: int | None = Field(None, description="Child's race ID")
    qr_token: str | None = Field(None, description="QR token for the child account")
    parent_id: str | None = Field(None, description="UUID of the parent account")
