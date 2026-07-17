from enum import Enum
from logging import Logger

from twilio.rest import Client

from src.Utils.EnvironmentFetch import fetch_bool_environment_variable, fetch_environment_variable

_DEV_BYPASS_VERIFICATION_CODE = "123456"


class VerificationStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    NOT_FOUND = "not_found"


class VerificationService:
    def __init__(self, logger: Logger):
        self.logger = logger
        self.SEND_VERIFICATION_MESSAGES = fetch_bool_environment_variable(
            "SEND_VERIFICATION_MESSAGES"
        )
        self.twilio_client = Client(
            fetch_environment_variable("TWILIO_API_KEY"),
            fetch_environment_variable("TWILIO_API_SECRET"),
            fetch_environment_variable("TWILIO_ACCOUNT_SID"),
        )
        self.verify_service_sid = fetch_environment_variable("TWILIO_VERIFY_SERVICE_SID")

    def _to_e164(self, phone_number: str) -> str:
        if phone_number.startswith("+"):
            return phone_number
        if len(phone_number) == 10:
            return f"+1{phone_number}"
        raise ValueError(f"Cannot normalize phone number to E.164: {phone_number}")

    def _phone_suffix_for_log(self, phone_number: str) -> str:
        return phone_number[-4:] if len(phone_number) >= 4 else "****"

    def send_sms_verification_code(self, phone_number: str) -> VerificationStatus:
        formatted_phone_number = self._to_e164(phone_number)
        if not self.SEND_VERIFICATION_MESSAGES:
            self.logger.warning(
                "SEND_VERIFICATION_MESSAGES is false; skipping SMS (dev bypass, "
                "number ending in %s)",
                self._phone_suffix_for_log(formatted_phone_number),
            )
            return VerificationStatus.PENDING

        self.logger.info(
            "Sending SMS verification via Twilio (number ending in %s)",
            self._phone_suffix_for_log(formatted_phone_number),
        )
        verification = self.twilio_client.verify.services(
            self.verify_service_sid
        ).verifications.create(to=formatted_phone_number, channel="sms")

        if verification.status is None:
            self.logger.error(
                "Twilio verification create returned no status (number ending in %s)",
                self._phone_suffix_for_log(formatted_phone_number),
            )
            raise ValueError("Failed to send verification code")

        self.logger.info(
            "SMS verification dispatched, Twilio status=%s (number ending in %s)",
            verification.status,
            self._phone_suffix_for_log(formatted_phone_number),
        )

        if verification.status == VerificationStatus.APPROVED.value:
            return VerificationStatus.APPROVED
        elif verification.status == VerificationStatus.PENDING.value:
            return VerificationStatus.PENDING
        else:
            raise ValueError("Invalid verification status")

    # To be implemented
    def send_email_verification_code(self, email: str) -> VerificationStatus:
        return VerificationStatus.PENDING

    def verify_verification_code(self, phone_number: str, verification_code: str) -> bool:
        formatted_phone_number = self._to_e164(phone_number)
        if not self.SEND_VERIFICATION_MESSAGES:
            self.logger.info(
                "Checking dev bypass verification code (number ending in %s)",
                self._phone_suffix_for_log(formatted_phone_number),
            )
            if verification_code != _DEV_BYPASS_VERIFICATION_CODE:
                self.logger.warning(
                    "Dev bypass verification failed (number ending in %s)",
                    self._phone_suffix_for_log(formatted_phone_number),
                )
                return False

            return True

        self.logger.info(
            "Checking SMS verification code (number ending in %s)",
            self._phone_suffix_for_log(formatted_phone_number),
        )
        check = self.twilio_client.verify.v2.services(
            self.verify_service_sid
        ).verification_checks.create(
            to=formatted_phone_number,
            code=verification_code,
        )
        if check.status != VerificationStatus.APPROVED.value:
            self.logger.warning(
                "SMS verification check failed, Twilio status=%s (number ending in %s)",
                check.status,
                self._phone_suffix_for_log(formatted_phone_number),
            )
            return False

        return True

    # To be implemented
    def verify_verification_code_email(self, email: str, verification_code: str) -> bool:
        return True
