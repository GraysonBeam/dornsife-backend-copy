import os
from datetime import UTC, datetime, timedelta
from logging import Logger, getLogger
from unittest.mock import MagicMock

os.environ.setdefault("VERIFICATION_TTL", "1440")

import pytest

from src.Models.exceptions import NotFoundException, RegistrationExpiredException
from src.Models.PendingRegistration import PendingRegistration
from src.Services.ResendVerificationService import ResendVerificationService
from src.Services.VerificationService import VerificationStatus


@pytest.fixture
def logger():
    return getLogger("resend_verification_service_test")


@pytest.fixture
def mock_pending_reg_repo():
    return MagicMock()


@pytest.fixture
def mock_verification_service():
    return MagicMock()


@pytest.fixture
def resend_service(
    logger: Logger, mock_pending_reg_repo: MagicMock, mock_verification_service: MagicMock
):
    return ResendVerificationService(logger, mock_pending_reg_repo, mock_verification_service)


def _make_pending_reg(expired: bool) -> PendingRegistration:
    reg = MagicMock(spec=PendingRegistration)
    reg.ID = "test-id-123"
    reg.USER_ID = "user-456"
    if expired:
        reg.CREATED_AT = datetime(2020, 1, 1, tzinfo=UTC)
    else:
        reg.CREATED_AT = datetime.now(UTC) + timedelta(hours=1)
    return reg


def test_resend_success(
    resend_service: ResendVerificationService,
    mock_pending_reg_repo: MagicMock,
    mock_verification_service: MagicMock,
):
    pending_reg = _make_pending_reg(expired=False)
    mock_pending_reg_repo.get_registration_by_id.return_value = pending_reg
    mock_pending_reg_repo.get_user_email_from_pending_registration.return_value = "user@example.com"
    mock_verification_service.send_email_verification_code.return_value = VerificationStatus.PENDING

    resend_service.resend_verification("test-id-123", "email")

    mock_pending_reg_repo.get_registration_by_id.assert_called_once_with("test-id-123")
    mock_verification_service.send_email_verification_code.assert_called_once_with(
        "user@example.com"
    )


def test_resend_raises_not_found_when_registration_missing(
    resend_service: ResendVerificationService, mock_pending_reg_repo: MagicMock
):
    mock_pending_reg_repo.get_registration_by_id.return_value = None

    with pytest.raises(NotFoundException, match="Pending registration not found"):
        resend_service.resend_verification("nonexistent-id", "email")


def test_resend_raises_expired_when_expiration_date_is_past(
    resend_service: ResendVerificationService, mock_pending_reg_repo: MagicMock
):
    expired_reg = _make_pending_reg(expired=True)
    mock_pending_reg_repo.get_registration_by_id.return_value = expired_reg

    with pytest.raises(RegistrationExpiredException, match="expired"):
        resend_service.resend_verification("expired-id", "email")

    mock_pending_reg_repo.update_token_by_id.assert_not_called()
    mock_pending_reg_repo.get_user_email_from_pending_registration.assert_not_called()


def test_resend_raises_expired_for_naive_datetime(
    resend_service: ResendVerificationService, mock_pending_reg_repo: MagicMock
):
    reg = MagicMock(spec=PendingRegistration)
    reg.CREATED_AT = datetime(2020, 1, 1)  # naive, in the past
    mock_pending_reg_repo.get_registration_by_id.return_value = reg

    with pytest.raises(RegistrationExpiredException):
        resend_service.resend_verification("some-id", "sms")


def test_resend_raises_not_found_when_user_phone_number_missing(
    resend_service: ResendVerificationService,
    mock_pending_reg_repo: MagicMock,
    mock_verification_service: MagicMock,
):
    pending_reg = _make_pending_reg(expired=False)
    mock_pending_reg_repo.get_registration_by_id.return_value = pending_reg
    mock_pending_reg_repo.get_user_phone_number_from_pending_registration.return_value = None

    with pytest.raises(NotFoundException, match="User not found"):
        resend_service.resend_verification("test-id-123", "sms")

    mock_pending_reg_repo.update_token_by_id.assert_not_called()
    mock_verification_service.send_sms_verification_code.assert_not_called()


def test_resend_propagates_email_service_exception(
    resend_service: ResendVerificationService,
    mock_pending_reg_repo: MagicMock,
    mock_verification_service: MagicMock,
):
    pending_reg = _make_pending_reg(expired=False)
    mock_pending_reg_repo.get_registration_by_id.return_value = pending_reg
    mock_pending_reg_repo.get_user_email_from_pending_registration.return_value = "user@example.com"
    mock_verification_service.send_email_verification_code.side_effect = Exception("Twilio down")

    with pytest.raises(Exception, match="Twilio down"):
        resend_service.resend_verification("test-id-123", "email")
