from pydantic import BaseModel, Field


class ActivateAccountResponse(BaseModel):
    """Returned after a successful POST /accounts/activate."""

    qr_token: str = Field(description="The users QR token")
    uuid: str = Field(description="Users stable UUID")
    type: str = Field(description="Activation path type")
