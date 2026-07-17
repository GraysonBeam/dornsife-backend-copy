from __future__ import annotations

from logging import Logger
from typing import TYPE_CHECKING

from src.Models.exceptions import NotFoundException, RegistrationExpiredException
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Utils.ExpiredRegistration import get_expiration_datetime, is_registration_expired

if TYPE_CHECKING:
    from src.Services.VerificationService import VerificationService


class ResendVerificationService:
    def __init__(
        self,
        logger: Logger,
        pending_registration_repo: PendingRegistrationRepository,
        verification_service: VerificationService,
    ):
        self.logger = logger
        self.pending_registration_repo = pending_registration_repo
        self.verification_service = verification_service

    def resend_verification(self, pending_registration_id: str, verification_type: str) -> None:
        self.logger.info(
            "Processing resend verification for pending registration %s",
            pending_registration_id,
        )

        pending_reg = self.pending_registration_repo.get_registration_by_id(pending_registration_id)

        if pending_reg is None:
            self.logger.error("Pending registration %s not found", pending_registration_id)
            raise NotFoundException("Pending registration not found")

        expiry = get_expiration_datetime(pending_reg)

        if is_registration_expired(pending_reg):
            self.logger.warning(
                "Pending registration %s is expired (expired at %s)",
                pending_registration_id,
                expiry,
            )
            raise RegistrationExpiredException("Pending registration has expired")

        if verification_type == "email":
            user_email = self.pending_registration_repo.get_user_email_from_pending_registration(
                pending_registration_id
            )
            if user_email is None:
                self.logger.error(
                    "Could not resolve user email for pending registration %s",
                    pending_registration_id,
                )
                raise NotFoundException("User not found for pending registration")
            self.verification_service.send_email_verification_code(user_email)
            self.logger.info(
                "Resent verification email to %s for pending registration %s",
                user_email,
                pending_registration_id,
            )

        else:
            user_phone_number = (
                self.pending_registration_repo.get_user_phone_number_from_pending_registration(
                    pending_registration_id
                )
            )
            if user_phone_number is None:
                self.logger.error(
                    "Could not resolve user email for pending registration %s",
                    pending_registration_id,
                )
                raise NotFoundException("User not found for pending registration")
            self.verification_service.send_sms_verification_code(user_phone_number)
            self.logger.info(
                "Resent verification sms message to %s for pending registration %s",
                user_phone_number,
                pending_registration_id,
            )
