from pydantic import BaseModel, Field


class EventCreatedResponse(BaseModel):
    id: str = Field(description="The id of the event")
    status: str = Field(description="status of the creation")
