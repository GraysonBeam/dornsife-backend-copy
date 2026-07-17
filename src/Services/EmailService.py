import os
from logging import Logger

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from src.Utils.Validators import ValidationError, Validator


class EmailService:
    api_key: str
    from_email: str
    verification_template_id: str

    def __init__(self, logger: Logger):
        self.logger = logger

        api_key = os.getenv("SENDGRID_API_KEY")
        if not api_key:
            self.logger.error("SENDGRID_API_KEY not found")
            raise ValueError("SENDGRID_API_KEY not found")
        self.api_key = api_key

        from_email = os.getenv("SENDGRID_FROM_EMAIL")
        if not from_email:
            self.logger.error("SENDGRID_FROM_EMAIL not found")
            raise ValueError("SENDGRID_FROM_EMAIL not found")
        self.from_email = from_email

        verification_template_id = os.getenv("SENDGRID_VERIFICATION_TEMPLATE_ID")
        if not verification_template_id:
            self.logger.error("SENDGRID_VERIFICATION_TEMPLATE_ID not found")
            raise ValueError("SENDGRID_VERIFICATION_TEMPLATE_ID not found")
        self.verification_template_id = verification_template_id

        self.client = SendGridAPIClient(self.api_key)
        self.logger.info("EmailService initialized successfully")

    def send_verification_email(self, to_email: str, verification_code: str) -> bool:
        try:
            self.logger.info(f"Validating email: {to_email}")
            to_email = Validator.validate_email(to_email)
            self.logger.info(f"Email validated: {to_email}")

            self.logger.info("Validating verification code")
            Validator.validate_verification_token(verification_code)
            self.logger.info("Verification code validated")

        except ValidationError as e:
            self.logger.error(f"Validation failed: {str(e)}")
            raise

        try:
            # Use normalized email (lowercase, standardized)
            message = Mail(from_email=self.from_email, to_emails=to_email)
            message.template_id = self.verification_template_id
            message.dynamic_template_data = {"verification_code": verification_code}

            response = self.client.send(message)

            if 200 <= response.status_code < 300:
                self.logger.info(f"Verification email sent successfully to {to_email}")
                return True
            else:
                self.logger.error(f"SendGrid failed with status: {response.status_code}")
                raise Exception(f"SendGrid returned status: {response.status_code}")

        except Exception as e:
            self.logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            raise
