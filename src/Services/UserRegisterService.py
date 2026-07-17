from logging import Logger

from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.RaceOptionsResponse import RaceOptionItem
from src.Schemas.UserRegistrationRequest import UserRegistrationRequest
from src.Services.VerificationService import VerificationService, VerificationStatus
from src.Utils.QrGenerator import generate_qr_token


class UserRegisterService:
    def __init__(
        self,
        logger: Logger,
        userRepository: UsersRepository,
        pendingRegistrationRepository: PendingRegistrationRepository,
        verificationService: VerificationService,
    ):
        self.logger = logger
        self.userRepository = userRepository
        self.PendingRegistrationRepository = pendingRegistrationRepository
        self.verificationService = verificationService

    def get_race_options(self) -> list[RaceOptionItem] | None:
        """Returns race options as key (label) + id for the client."""
        res = self.userRepository.get_all_races_from_db()
        if not res:
            return None
        return [RaceOptionItem(key=description, id=race_id) for race_id, description in res]

    def create_inactive_user(self, user_data: UserRegistrationRequest) -> str:
        # Create Inactive User
        new_user = self.userRepository.add_user(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            phone_number=user_data.phone_number,
            date_of_birth=user_data.date_of_birth,
            zip_code=user_data.zip_code,
            address=user_data.address,
            race_id=user_data.race_id,
            qr_token=generate_qr_token(),
            parent_id=None,
        )
        self.logger.info(f"Created new user with id: {new_user.id}")

        # Create Pending Registration
        pending_reg_id = self.PendingRegistrationRepository.insert_pending_registration(
            user_id=new_user.id,
        )
        self.logger.info(f"Created pending registration for user id: {new_user.id}")

        if user_data.phone_number:
            self.logger.info(
                "Sending verification sms message for pending reg id %s linked to user id %s",
                pending_reg_id,
                new_user.id,
            )
            result = self.verificationService.send_sms_verification_code(user_data.phone_number)
            if result != VerificationStatus.PENDING:
                self.logger.error(
                    "Verification code for sms failed in Twilio, status=%s, phone_number=%s",
                    result,
                    user_data.phone_number,
                )
                raise Exception("Verification code for sms failed to create")

        if user_data.email:
            self.logger.info(
                "Sending verification email for pending reg id %s linked to user id %s",
                pending_reg_id,
                new_user.id,
            )
            result = self.verificationService.send_email_verification_code(user_data.email)
            if result != VerificationStatus.PENDING:
                self.logger.error(
                    "Verification code for email failed in Twilio, status=%s, phone_number=%s",
                    result,
                    user_data.email,
                )
                raise Exception("Verification code for email failed to create")

        return pending_reg_id
