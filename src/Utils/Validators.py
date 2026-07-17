import re
from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from email_validator import EmailNotValidError, validate_email

PHONE_FORMATTING_CHARACTERS = ("-", " ", "(", ")", "+")


class ValidationError(Exception):
    """Custom exception for validation errors."""

    pass


class Validator:
    @staticmethod
    def validate_email(email: str, check_deliverability: bool = False) -> str:
        try:
            # Validate email
            emailinfo = validate_email(email, check_deliverability=check_deliverability)

            # Return normalized email (lowercase, standardized)
            normalized_email = emailinfo.normalized

            return normalized_email

        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email: {str(e)}") from e

    @staticmethod
    def validate_verification_token(verification_code: str) -> bool:
        if len(verification_code) != 6:
            raise ValidationError("Verification code must be exactly 6 digits")

        if not verification_code.isdigit():
            raise ValidationError("Verification code must contain only digits")

        return True

    @staticmethod
    def validate_required_string(value: str, field_name: str) -> str:
        if not value or not value.strip():
            raise ValidationError(f"{field_name} is required")
        return value.strip()

    @staticmethod
    def validate_contact_fields(
        email: str | None,
        phone_number: str | None,
        *,
        require_one: bool,
        missing_message: str = "At least one of email or phone_number must be provided",
    ) -> tuple[str | None, str | None]:
        normalized_email = email.strip() or None if email is not None else None
        normalized_phone_number = phone_number.strip() or None if phone_number is not None else None

        if require_one and not normalized_email and not normalized_phone_number:
            raise ValidationError(missing_message)

        if normalized_email and normalized_phone_number:
            raise ValidationError("Cannot provide both email and phone_number")

        validated_email = (
            Validator.validate_email(normalized_email.lower()) if normalized_email else None
        )
        validated_phone_number = (
            Validator.validate_phone_number(normalized_phone_number)
            if normalized_phone_number
            else None
        )

        return validated_email, validated_phone_number

    @staticmethod
    def validate_phone_number(phone_number: str) -> str:
        if not phone_number:
            return phone_number

        # TODO: change depending on how frontend sends the data
        cleaned = phone_number
        for character in PHONE_FORMATTING_CHARACTERS:
            cleaned = cleaned.replace(character, "")

        if not cleaned.isdigit():
            raise ValidationError(
                "Phone number must contain only digits and common formatting characters"
            )

        if len(cleaned) < 10 or len(cleaned) > 15:
            raise ValidationError("Phone number must be between 10 and 15 digits")

        return cleaned

    @staticmethod
    def validate_date_of_birth(date_input: str | date | None) -> date | None:
        if not date_input:
            return None

        if isinstance(date_input, date):
            date_obj = date_input
        else:
            try:
                date_obj = datetime.strptime(date_input, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValidationError("Date of birth must be in YYYY-MM-DD format") from e

        # Check if date is not in the future
        if date_obj > date.today():
            raise ValidationError("Date of birth cannot be in the future")

        # Check if person is not too old (e.g., 150 years)
        age_days = (date.today() - date_obj).days
        age_years = age_days / 365.25
        if age_years > 150:
            raise ValidationError("Invalid date of birth: age exceeds reasonable limit")

        return date_obj

    @staticmethod
    def validate_zip_code(zip_code: str) -> str:
        if not zip_code:
            return zip_code

        # possible zipcode format 12345 or 12345-6789
        pattern = r"^\d{5}(-\d{4})?$"

        if not re.match(pattern, zip_code):
            raise ValidationError("Zip code must be in format 12345 or 12345-6789")

        return zip_code

    @staticmethod
    def validate_uuid_string(val: str) -> bool:
        try:
            UUID(str(val))
            return True
        except ValueError as e:
            raise ValidationError("ID must be valid uuid") from e

    @staticmethod
    def validate_event_time(start_time: datetime, end_time: datetime) -> None:
        """Validate event start and end times.

        Converts naive datetimes to UTC and validates.
        """
        # Convert naive datetimes to UTC-aware using astimezone()
        if start_time.tzinfo is None:
            start_time = start_time.astimezone(UTC)

        if end_time.tzinfo is None:
            end_time = end_time.astimezone(UTC)

        # Check end is after start
        if end_time <= start_time:
            raise ValidationError("end_datetime must be after start_datetime")

        # Check start is not in past
        now = datetime.now(UTC)

        if start_time < now - timedelta(seconds=1):
            raise ValidationError("start_datetime cannot be in the past")
