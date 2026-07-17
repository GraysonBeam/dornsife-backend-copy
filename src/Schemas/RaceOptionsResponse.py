from pydantic import BaseModel, Field


class RaceOptionItem(BaseModel):
    """One ethnicity/race choice for registration UI."""

    key: str = Field(description="Label to show in dropdowns")
    id: int = Field(description="Numeric race_id")


class RaceOptionsResponse(BaseModel):
    """Race lookup list from GET /userRegistration/raceOptions."""

    races: list[RaceOptionItem] = Field(description="Key and id for each race option")
