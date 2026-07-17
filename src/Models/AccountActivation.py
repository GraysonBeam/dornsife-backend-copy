from enum import Enum


class ActivationType(Enum):
    NEW_ACCOUNT = "init_account"
    UPDATE_EMAIL = "update_email"
    UPDATE_PHONE_NUMBER = "update_phone_number"


class AccountActivation:
    def __init__(self, qr_token: str, uuid: str, type: ActivationType):
        self.qr_token: str = qr_token
        self.uuid: str = uuid
        # What type of activation happened (new account activation or update email verification)
        self.type: ActivationType = type
