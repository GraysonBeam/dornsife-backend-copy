import logging
from logging import Logger
from unittest.mock import Mock, patch

import pytest
from pytest import MonkeyPatch

from src.Services.EmailService import EmailService
from src.Utils.Validators import ValidationError


@pytest.fixture
def logger() -> Logger:
    """Create a test logger"""
    return logging.getLogger("test")


@pytest.fixture
def mock_env_vars(monkeypatch: MonkeyPatch) -> None:
    """Set up valid environment variables"""
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key-123")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "test@example.com")
    monkeypatch.setenv("SENDGRID_VERIFICATION_TEMPLATE_ID", "template-abc-123")


# successful email send


@patch("src.Services.EmailService.SendGridAPIClient")
def test_send_email_success(mock_sendgrid_class: Mock, logger: Logger, mock_env_vars: None) -> None:
    """Test successful email send with 202 status"""
    # Setup mock
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 202
    mock_client.send.return_value = mock_response
    mock_sendgrid_class.return_value = mock_client

    # Create service and send
    service = EmailService(logger)
    service.send_verification_email("user@example.com", "123456")

    # Verify send was called
    assert mock_client.send.called


@patch("src.Services.EmailService.SendGridAPIClient")
def test_send_email_returns_true_on_success(
    mock_sendgrid_class: Mock, logger: Logger, mock_env_vars: None
) -> None:
    """Test that send_verification_email returns True on success"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 200
    mock_client.send.return_value = mock_response
    mock_sendgrid_class.return_value = mock_client

    service = EmailService(logger)
    result = service.send_verification_email("user@example.com", "123456")

    assert result is True


# missing environment variables


def test_missing_api_key(logger: Logger, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("SENDGRID_API_KEY", raising=False)
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "test@example.com")
    monkeypatch.setenv("SENDGRID_VERIFICATION_TEMPLATE_ID", "template-123")

    with pytest.raises(ValueError, match="SENDGRID_API_KEY not found"):
        EmailService(logger)


def test_missing_from_email(logger: Logger, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key-123")
    monkeypatch.delenv("SENDGRID_FROM_EMAIL", raising=False)
    monkeypatch.setenv("SENDGRID_VERIFICATION_TEMPLATE_ID", "template-123")

    with pytest.raises(ValueError, match="SENDGRID_FROM_EMAIL not found"):
        EmailService(logger)


def test_missing_verification_template_id(logger: Logger, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setenv("SENDGRID_API_KEY", "test-api-key-123")
    monkeypatch.setenv("SENDGRID_FROM_EMAIL", "test@example.com")
    monkeypatch.delenv("SENDGRID_VERIFICATION_TEMPLATE_ID", raising=False)

    with pytest.raises(ValueError, match="SENDGRID_VERIFICATION_TEMPLATE_ID not found"):
        EmailService(logger)


# invalid send_verification_email parameters
@patch("src.Services.EmailService.SendGridAPIClient")
def test_verification_code_not_6_digits(
    mock_sendgrid: Mock, logger: Logger, mock_env_vars: None
) -> None:
    service = EmailService(logger)

    with pytest.raises(ValidationError, match="exactly 6 digits"):
        service.send_verification_email("user@example.com", "12345")


@patch("src.Services.EmailService.SendGridAPIClient")
def test_verification_code_too_long(
    mock_sendgrid: Mock, logger: Logger, mock_env_vars: None
) -> None:
    service = EmailService(logger)

    with pytest.raises(ValidationError, match="exactly 6 digits"):
        service.send_verification_email("user@example.com", "1234567")


@patch("src.Services.EmailService.SendGridAPIClient")
def test_verification_code_has_letters(
    mock_sendgrid: Mock, logger: Logger, mock_env_vars: None
) -> None:
    service = EmailService(logger)

    with pytest.raises(ValidationError, match="contain only digits"):
        service.send_verification_email("user@example.com", "12a456")


@patch("src.Services.EmailService.SendGridAPIClient")
def test_invalid_to_email_missing_at_symbol(
    mock_sendgrid: Mock, logger: Logger, mock_env_vars: None
) -> None:
    service = EmailService(logger)

    with pytest.raises(ValidationError, match="Invalid email"):
        service.send_verification_email("user", "012345")


@patch("src.Services.EmailService.SendGridAPIClient")
def test_invalid_to_email_missing_domain(
    mock_sendgrid: Mock, logger: Logger, mock_env_vars: None
) -> None:
    service = EmailService(logger)

    with pytest.raises(ValidationError, match="Invalid email"):
        service.send_verification_email("user@gmail", "012345")


@patch("src.Services.EmailService.SendGridAPIClient")
def test_invalid_to_email_empty_string(
    mock_sendgrid: Mock, logger: Logger, mock_env_vars: None
) -> None:
    service = EmailService(logger)

    with pytest.raises(ValidationError, match="Invalid email"):
        service.send_verification_email("", "123456")


# bad http response


@patch("src.Services.EmailService.SendGridAPIClient")
def test_bad_http_status_raises_exception(
    mock_sendgrid_class: Mock, logger: Logger, mock_env_vars: None
) -> None:
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 400
    mock_client.send.return_value = mock_response
    mock_sendgrid_class.return_value = mock_client

    service = EmailService(logger)

    with pytest.raises(Exception, match="status: 400"):
        service.send_verification_email("user@example.com", "123456")


# sendgrid api failure


@patch("src.Services.EmailService.SendGridAPIClient")
def test_sendgrid_api_exception(
    mock_sendgrid_class: Mock, logger: Logger, mock_env_vars: None
) -> None:
    mock_client = Mock()
    mock_client.send.side_effect = Exception("SendGrid API Error")
    mock_sendgrid_class.return_value = mock_client

    service = EmailService(logger)

    with pytest.raises(Exception, match="SendGrid API Error"):
        service.send_verification_email("user@example.com", "123456")


# edge cases


@patch("src.Services.EmailService.SendGridAPIClient")
def test_send_email_with_all_zeros_code(
    mock_sendgrid_class: Mock, logger: Logger, mock_env_vars: None
) -> None:
    """Test sending email with verification code of all zeros (valid edge case)"""
    mock_client = Mock()
    mock_response = Mock()
    mock_response.status_code = 202
    mock_client.send.return_value = mock_response
    mock_sendgrid_class.return_value = mock_client

    service = EmailService(logger)
    result = service.send_verification_email("user@example.com", "000000")

    assert result is True
    assert mock_client.send.called
