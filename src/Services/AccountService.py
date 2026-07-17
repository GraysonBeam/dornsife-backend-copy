from collections import defaultdict
from datetime import date
from logging import Logger

from src.Models.AccountActivation import AccountActivation, ActivationType
from src.Models.DisplayUserRecord import DisplayUserRecord
from src.Models.exceptions import NotFoundException
from src.Models.PendingRegistration import PendingRegistration
from src.Models.User import User
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.AddChildRequest import AddChildRequest
from src.Schemas.AddChildResponse import AddChildResponse
from src.Services.VerificationService import VerificationService
from src.Utils.QrGenerator import generate_qr_token
from src.Utils.Validators import ValidationError, Validator


class AccountService:
    def __init__(
        self,
        logger: Logger,
        pendingRegistrationRepository: PendingRegistrationRepository,
        usersRepository: UsersRepository,
        verificationService: VerificationService,
    ):
        self.logger = logger
        self.pendingRegistrationRepository = pendingRegistrationRepository
        self.usersRepository = usersRepository
        self.verificationService = verificationService

    def init_activate_account(self, user: User) -> AccountActivation:
        self.logger.info("Setting User id %s status to active", user.id)
        self.usersRepository.set_active_status(user, is_active=True)

        self.logger.info("Account activated successfully")

        if user.qr_token is None:
            raise ValueError("QR Token is required to activate account")

        return AccountActivation(user.qr_token, str(user.id), ActivationType.NEW_ACCOUNT)

    def update_account_with_email(self, user: User, new_email: str) -> AccountActivation:
        self.logger.info("Updating email of User %s to %s", user.id, new_email)
        self.usersRepository.set_email(user, new_email)

        if user.qr_token is None:
            raise ValueError("QR Token is required to activate account")

        return AccountActivation(user.qr_token, str(user.id), ActivationType.UPDATE_EMAIL)

    def update_account_with_phone_number(
        self, user: User, new_phone_number: str
    ) -> AccountActivation:
        self.logger.info("Updating phone number of User %s to %s", user.id, new_phone_number)
        self.usersRepository.set_phone_number(user, new_phone_number)

        if user.qr_token is None:
            raise ValueError("QR Token is required to activate account")

        return AccountActivation(user.qr_token, str(user.id), ActivationType.UPDATE_PHONE_NUMBER)

    def verify_account(
        self,
        pending_reg: PendingRegistration,
        user: User,
        verification_code: str,
        verification_type: str,
    ) -> None:
        # We are verifying a new phone number / email or an existing user phone number / email,
        # with priority given to a new phone number / email if it is present
        if verification_type == "sms":
            if pending_reg.NEW_PHONE_NUMBER is not None:
                good_phone_number = pending_reg.NEW_PHONE_NUMBER
            elif user.phone_number is not None:
                good_phone_number = user.phone_number
            else:
                self.logger.error(
                    f"No valid phone number found for user id {user.id} or pending_reg {id}"
                )
                raise ValidationError("Invalid phone number")

            result = self.verificationService.verify_verification_code(
                good_phone_number, verification_code
            )

        else:
            if pending_reg.NEW_EMAIL is not None:
                good_email = pending_reg.NEW_EMAIL
            elif user.email is not None:
                good_email = user.email
            else:
                self.logger.error(f"No valid email found for user id {user.id} or pending_reg {id}")
                raise ValidationError("Invalid email")

            result = self.verificationService.verify_verification_code_email(
                good_email, verification_code
            )

        if not result:
            self.logger.error(
                f"Verification with code {verification_code} and type {verification_type} failed."
            )
            raise ValidationError("Failed verification with code using type %s", verification_type)

    def process_account_activation(
        self, id: str, verification_code: str, verification_type: str
    ) -> AccountActivation:
        pending_reg: PendingRegistration | None = (
            self.pendingRegistrationRepository.get_registration_by_id(id)
        )

        if pending_reg is None:
            self.logger.error(
                "Pending registration with id %s not found.",
                id,
            )
            raise NotFoundException("Pending Registration not found")

        self.logger.info("Getting User %s", pending_reg.USER_ID)
        user: User | None = self.usersRepository.get_user_by_id(user_id=pending_reg.USER_ID)

        if user is None:
            self.logger.error("User with id %s not found", pending_reg.USER_ID)
            raise NotFoundException("User not found")

        self.verify_account(pending_reg, user, verification_code, verification_type)

        activation: AccountActivation | None = None

        if pending_reg.NEW_EMAIL is not None:
            activation = self.update_account_with_email(user, pending_reg.NEW_EMAIL)
        elif pending_reg.NEW_PHONE_NUMBER is not None:
            activation = self.update_account_with_phone_number(user, pending_reg.NEW_PHONE_NUMBER)
        else:
            activation = self.init_activate_account(user=user)

        self.logger.info("Deleting Pending Registration %s", id)
        delete_res: str | None = self.pendingRegistrationRepository.delete_registration_by_id(id)

        if delete_res is None or "not found" in delete_res:
            self.logger.error("Pending Registration with id %s was not found to be deleted", id)
            raise NotFoundException("Pending Registration not found")

        return activation

    def get_user_profile_by_uuid(self, uuid: str) -> defaultdict[str, str | None] | None:
        """Returns dictionary of items derived from user profiles"""
        user = self.usersRepository.get_user_by_id(uuid)

        if not user:
            self.logger.error(f"User {uuid} does not exist")
            return None

        if not user.is_active:
            self.logger.info(f"User {uuid} is not active")
            return None

        res: defaultdict[str, str | None] = defaultdict(str)

        dob_str = user.date_of_birth.strftime("%Y-%m-%d") if user.date_of_birth else ""

        res["first_name"] = user.first_name or ""
        res["last_name"] = user.last_name or ""
        res["email"] = user.email or ""
        res["phone_number"] = user.phone_number or ""
        res["date_of_birth"] = dob_str
        res["zip_code"] = user.zip_code or ""
        res["address"] = user.address or ""
        res["race"] = self.usersRepository.get_race(uuid, user.race_id)

        return res

    def lookup_users(
        self, email: str | None = None, phone_number: str | None = None
    ) -> list[dict[str, str | None]]:
        self.logger.info(f"Looking up users by email={email} or phone={phone_number}")

        users = []
        if email:
            users = self.usersRepository.get_users_by_email(email)
        elif phone_number:
            users = self.usersRepository.get_users_by_phone_number(phone_number)

        res = []
        for user in users:
            dob_str = user.date_of_birth.strftime("%Y-%m-%d") if user.date_of_birth else ""

            user_data = {
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
                "phone_number": user.phone_number,
                "date_of_birth": dob_str,
                "zip_code": user.zip_code,
                "address": user.address,
                "race": self.usersRepository.get_race(str(user.id), user.race_id),
                "qr_token": user.qr_token,
            }
            res.append(user_data)

        return res

    def _create_pending_registration_and_send_verification(
        self, user_id: str, new_email: str | None, new_phone_number: str | None
    ) -> str:
        new_email, new_phone_number = Validator.validate_contact_fields(
            new_email,
            new_phone_number,
            require_one=False,
        )

        if new_email is None and new_phone_number is None:
            raise ValueError("")

        if new_email is not None:
            self.logger.info(
                "Email change requested for user %s — initiating verification", user_id
            )
            self.verificationService.send_email_verification_code(new_email)

            self.logger.info("Verification email sent to %s", new_email)

        if new_phone_number is not None:
            self.logger.info(
                "Phone number change request for user %s - initiating verification", user_id
            )
            self.verificationService.send_sms_verification_code(new_phone_number)
            self.logger.info("Verification message sent to %s", new_phone_number)

        pending_reg_id = self.pendingRegistrationRepository.insert_pending_registration(
            user_id=user_id,
            new_email=new_email if new_email is not None else "",
            new_phone_number=new_phone_number if new_phone_number is not None else "",
        )

        if new_email:
            message = f"email {new_email}"
        else:
            message = f"phone number {new_phone_number}"

        self.logger.info(
            "Created pending registration %s for contact update to %s", pending_reg_id, message
        )

        return pending_reg_id

    def update_user_profile(
        self,
        uuid: str,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
        phone_number: str | None = None,
        date_of_birth: date | None = None,
        zip_code: str | None = None,
        address: str | None = None,
        race_id: int | None = None,
    ) -> dict[str, str | None]:
        self.logger.info("Resolving user for profile update: %s", uuid)
        user = self.usersRepository.get_user_by_id(uuid)

        if user is None:
            self.logger.warning("User %s not found for profile update", uuid)
            raise NotFoundException("User not found")

        if not user.is_active:
            self.logger.warning("User %s is inactive — update rejected", uuid)
            raise NotFoundException("User not found")

        has_non_contact_changes = any(
            v is not None
            for v in [
                first_name,
                last_name,
                phone_number,
                date_of_birth,
                zip_code,
                address,
                race_id,
            ]
        )
        has_email_change = email is not None
        has_phone_number_change = phone_number is not None

        if has_non_contact_changes:
            result = self.usersRepository.update_user_fields(
                uuid,
                first_name=first_name,
                last_name=last_name,
                date_of_birth=date_of_birth,
                zip_code=zip_code,
                address=address,
                race_id=race_id,
            )
            if result in ("user_not_found", "user_inactive"):
                raise NotFoundException("User not found")
            self.logger.info("Non-email fields updated for user %s", uuid)

        if has_email_change or has_phone_number_change:
            pending_reg_id = self._create_pending_registration_and_send_verification(
                user_id=uuid, new_email=email, new_phone_number=phone_number
            )

            return {
                "message": (
                    "A verification message has been sent to the new address. "
                    "Non-contact fields (if any) have been updated immediately."
                    if has_non_contact_changes
                    else "A verification message has been sent to the new address."
                ),
                "pending_registration_id": pending_reg_id,
            }

        updated_profile = self.get_user_profile_by_uuid(uuid)
        if updated_profile is None:
            raise NotFoundException("User not found")

        return {
            "message": "Profile updated successfully.",
            **updated_profile,
        }

    def add_child(self, request: AddChildRequest) -> AddChildResponse:
        self.logger.info("Adding child to parent %s", request.parent_id)
        Validator.validate_uuid_string(request.parent_id)

        parent = self.usersRepository.get_user_by_id(request.parent_id)
        if not parent:
            raise NotFoundException(f"Parent {request.parent_id} not found")

        if not parent.is_active:
            raise NotFoundException(f"Parent {request.parent_id} is not active")

        if not parent.email and not parent.phone_number:
            raise NotFoundException(f"Parent {request.parent_id} is missing email or phone number")

        if parent.email and parent.phone_number:
            raise ValidationError("Parent cannot have both email and phone number")

        qr_token = generate_qr_token()
        child = self.usersRepository.add_user(
            first_name=request.first_name,
            last_name=request.last_name,
            email=parent.email,
            phone_number=parent.phone_number,
            date_of_birth=request.date_of_birth,
            zip_code=request.zip_code,
            address=request.address,
            race_id=request.race_id,
            qr_token=qr_token,
            parent_id=parent.id,
            is_active=True,
        )

        self.logger.info("Child %s added to parent %s", child.id, parent.id)

        return AddChildResponse(
            id=child.id,
            first_name=child.first_name,
            last_name=child.last_name,
            email=child.email,
            phone_number=child.phone_number,
            date_of_birth=str(child.date_of_birth) if child.date_of_birth else None,
            zip_code=child.zip_code,
            address=child.address,
            race_id=child.race_id,
            qr_token=qr_token,
            parent_id=str(parent.id),
        )

    def get_users_paginated(self, page: int, page_size: int) -> list[DisplayUserRecord]:
        self.logger.info("Retrieving users paginated: page %s, page size %s", page, page_size)
        return self.usersRepository.get_users_paginated(page, page_size)
