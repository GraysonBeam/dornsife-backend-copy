from datetime import UTC, datetime, timedelta

from src.Constants.Constants import PENDING_REGISTRATION_EXPIRY_MINUTES
from src.Models.PendingRegistration import PendingRegistration


def get_expiration_datetime(pending_reg: PendingRegistration) -> datetime:
    created_at = pending_reg.CREATED_AT
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)

    return created_at + timedelta(minutes=PENDING_REGISTRATION_EXPIRY_MINUTES)


def is_registration_expired(pending_reg: PendingRegistration) -> bool:
    current_time = datetime.now(UTC)

    expiration_time = get_expiration_datetime(pending_reg)
    if current_time >= expiration_time:
        return True

    return False
