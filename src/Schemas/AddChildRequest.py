from pydantic import BaseModel, Field


class AddChildRequest(BaseModel):
    parent_id: str = Field(..., description="UUID of the parent account")
    first_name: str = Field(..., description="Child's first name")
    last_name: str = Field(..., description="Child's last name")
    date_of_birth: str = Field(..., description="Child's date of birth")
    zip_code: str = Field(..., description="Child's zip code")
    address: str = Field(..., description="Child's address")
    race_id: int = Field(..., description="Child's race ID")
