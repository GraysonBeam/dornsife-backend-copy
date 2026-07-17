from dataclasses import dataclass


@dataclass
class DisplayUserRecord:
    first_name: str | None
    last_name: str | None
    email: str | None
    phone_number: str | None
    date_of_birth: str | None
    zip_code: str | None
    address: str | None
    race_description: str | None
    is_active: bool
    parent_first_name: str | None
    parent_last_name: str | None
