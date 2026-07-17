from __future__ import annotations

from logging import Logger

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.Models.exceptions import DatabaseErrorException
from src.Models.PendingRegistration import PendingRegistration
from src.Utils.Validators import Validator


class PendingRegistrationRepository:
    def __init__(self, logger: Logger, db: Session):
        self.logger = logger
        self.db = db

    def delete_registration_by_id(self, registration_id: str) -> str | None:
        self.logger.info("Attempting to extract pending registration from id")
        try:
            pending_reg = self.db.execute(
                select(PendingRegistration).where(PendingRegistration.ID == registration_id)
            ).scalar_one_or_none()

            if not pending_reg:
                return "pending registration not found"

            self.db.delete(pending_reg)
            self.logger.info(f"Deleted pending registration {registration_id} by ID")
            return f"Successfully deleted {registration_id} by id"

        except Exception as e:
            self.logger.error(f"Error with pending registration {registration_id}:", e)
            raise Exception("Error processing pending registration") from e

    def get_user_email_from_pending_registration(self, pending_registration_id: str) -> str | None:
        self.logger.info(
            f"Attempting to extract user email from pending registration {pending_registration_id}"
        )
        try:
            stmt = (
                select(PendingRegistration)
                .where(PendingRegistration.ID == pending_registration_id)
                .options(joinedload(PendingRegistration.user))
            )
            pending_reg = self.db.execute(stmt).scalar_one_or_none()

            self.logger.info(f"pending_reg == {type(pending_reg)}")

            if not pending_reg:
                self.logger.warning(
                    f"Pending registration {pending_registration_id} not found or expired"
                )
                return None

            email = pending_reg.user.email
            if pending_reg.NEW_EMAIL is not None:
                email = pending_reg.NEW_EMAIL

            self.logger.info(f"Successfully extracted email {pending_registration_id}")
            return email

        except Exception as e:
            self.logger.error(f"Error resolving email: {e}")
            raise

    def get_user_phone_number_from_pending_registration(self, pending_reg_id: str) -> str | None:
        self.logger.info(
            f"Attempting to extract user phone number from pending registration {pending_reg_id}"
        )
        try:
            stmt = (
                select(PendingRegistration)
                .where(PendingRegistration.ID == pending_reg_id)
                .options(joinedload(PendingRegistration.user))
            )
            pending_reg = self.db.execute(stmt).scalar_one_or_none()

            self.logger.info(f"pending_reg == {type(pending_reg)}")

            if not pending_reg:
                self.logger.warning(f"Pending registration {pending_reg_id} not found or expired")
                return None

            phone_number = pending_reg.user.phone_number
            if pending_reg.NEW_PHONE_NUMBER is not None:
                phone_number = pending_reg.NEW_PHONE_NUMBER

            self.logger.info(f"Successfully extracted phone number {pending_reg_id}")
            return phone_number

        except Exception as e:
            self.logger.error(f"Error resolving phone number: {e}")
            raise

    def get_registration_by_id(self, registration_id: str) -> PendingRegistration | None:
        """Fetches a pending registration by ID with no expiration filter."""
        self.logger.info("Fetching pending registration %s", registration_id)
        try:
            return self.db.execute(
                select(PendingRegistration).where(PendingRegistration.ID == registration_id)
            ).scalar_one_or_none()
        except Exception as e:
            self.logger.error("Error fetching pending registration %s: %s", registration_id, e)
            raise Exception("Error fetching pending registration") from e

    def _insert_email_update_pending_registration(self, user_id: str, new_email: str) -> str:
        self.logger.info("Inserting Pending Registration for email update")
        try:
            pending_reg = PendingRegistration(
                USER_ID=user_id,
                NEW_EMAIL=new_email,
            )
            self.db.add(pending_reg)
            self.db.flush()
            return pending_reg.ID
        except Exception as e:
            self.logger.error("Error while trying to insert new_email registration: %s", e)
            raise DatabaseErrorException(
                f"Database error inserting new_email registration {e}"
            ) from e

    def _insert_phone_number_update_pending_registration(
        self,
        user_id: str,
        new_phone_number: str,
    ) -> str:
        self.logger.info("")
        try:
            pending_reg = PendingRegistration(USER_ID=user_id, NEW_PHONE_NUMBER=new_phone_number)
            self.db.add(pending_reg)
            self.db.flush()
            return pending_reg.ID
        except Exception as e:
            self.logger.error("Error while trying to insert new_phone_number registration: %s", e)
            raise DatabaseErrorException(
                f"Database error inserting new_phone_number registration {e}"
            ) from e

    def _insert_new_user_pending_registration(
        self,
        user_id: str,
    ) -> str:
        self.logger.info("Inserting Pending Registration for new user")
        try:
            pending_reg = PendingRegistration(
                USER_ID=user_id,
            )
            self.db.add(pending_reg)
            self.db.flush()
            return pending_reg.ID
        except Exception as e:
            self.logger.error("Error inserting new Pending Registration: %s", e)
            raise DatabaseErrorException(f"Database Insert error {e}") from e

    def insert_pending_registration(
        self,
        user_id: str,
        new_email: str = "",
        new_phone_number: str = "",
    ) -> str:
        good_email, good_phone_number = Validator.validate_contact_fields(
            new_email,
            new_phone_number,
            require_one=False,
        )

        if good_email:
            return self._insert_email_update_pending_registration(user_id, good_email)
        if good_phone_number:
            return self._insert_phone_number_update_pending_registration(user_id, good_phone_number)

        return self._insert_new_user_pending_registration(user_id)
