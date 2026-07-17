import logging
from collections.abc import Generator
from logging import Logger
from unittest.mock import Mock

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.User import Base, RaceLookup
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.RaceOptionsResponse import RaceOptionItem
from src.Schemas.UserRegistrationRequest import UserRegistrationRequest
from src.Services.UserRegisterService import UserRegisterService
from src.Services.VerificationService import VerificationStatus

RaceOption = tuple[int, str]


# fixtures
@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def logger() -> Logger:
    return logging.getLogger("Test Logger")


@pytest.fixture
def test_race_lookup(db_session: Session) -> list[RaceOption]:
    mock_race_table = {
        1: "White",
        2: "Black or African American",
        3: "American Indian or Alaska Native",
        4: "Native Hawaiian Or Pacific Islander",
        5: "Hispanic or Latino",
        6: "Other",
    }

    race_lst: list[RaceOption] = []

    for _id, race in mock_race_table.items():
        race_obj = RaceLookup(race_id=_id, description=race)
        db_session.add(race_obj)
        db_session.commit()
        race_lst.append((race_obj.race_id, race_obj.description))

    return race_lst


@pytest.fixture
def test_user_register_service(logger: Logger, db_session: Session) -> UserRegisterService:
    mock_verification = Mock()
    mock_verification.send_sms_verification_code.return_value = VerificationStatus.PENDING
    mock_verification.send_email_verification_code.return_value = VerificationStatus.PENDING
    repo = UsersRepository(logger, db_session)
    pending_repo = PendingRegistrationRepository(logger, db_session)
    return UserRegisterService(logger, repo, pending_repo, mock_verification)


# test suites
def test_race_extraction_success(
    test_user_register_service: UserRegisterService, test_race_lookup: list[RaceOption]
) -> None:
    race_lst = test_user_register_service.get_race_options()
    expected = [
        RaceOptionItem(key=description, id=race_id) for race_id, description in test_race_lookup
    ]
    assert race_lst == expected, "Race list should be equal"


def test_race_extraction_fail(test_user_register_service: UserRegisterService) -> None:
    race_lst = test_user_register_service.get_race_options()
    assert race_lst is None, "Race list should return None"


def test_create_inactive_user_success(
    db_session: Session,
    logger: Logger,
    test_race_lookup: list[RaceOption],
    test_user_register_service: UserRegisterService,
):
    repo = UsersRepository(logger, db_session)
    pending_repo = PendingRegistrationRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.send_sms_verification_code.return_value = VerificationStatus.PENDING
    mock_ver.send_email_verification_code.return_value = VerificationStatus.PENDING
    service = UserRegisterService(logger, repo, pending_repo, mock_ver)

    user_data = UserRegistrationRequest(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        date_of_birth="1990-01-01",
        zip_code="12345",
        address="123 Main St",
        race_id=1,
    )

    pending_id = service.create_inactive_user(user_data)
    assert pending_id, "Pending registration id should be returned"

    # verify the pending registration maps back to the user email
    pending_repo_check = PendingRegistrationRepository(logger, db_session)
    extracted_email = pending_repo_check.get_user_email_from_pending_registration(pending_id)
    assert user_data.email is not None
    assert extracted_email == user_data.email


def test_create_inactive_user_sms_failure(
    db_session: Session, logger: Logger, test_race_lookup: list[RaceOption]
):
    repo = UsersRepository(logger, db_session)
    pending_repo = PendingRegistrationRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.send_sms_verification_code.return_value = VerificationStatus.APPROVED
    mock_ver.send_email_verification_code.return_value = VerificationStatus.PENDING
    service = UserRegisterService(logger, repo, pending_repo, mock_ver)

    user_data = UserRegistrationRequest(
        first_name="Test",
        last_name="User",
        phone_number="1234567890",
        date_of_birth="1990-01-01",
        zip_code="12345",
        address="123 Main St",
        race_id=1,
    )

    with pytest.raises(Exception) as excinfo:
        service.create_inactive_user(user_data)

    assert "sms" in str(excinfo.value).lower()


def test_create_inactive_user_email_failure(
    db_session: Session, logger: Logger, test_race_lookup: list[RaceOption]
):
    repo = UsersRepository(logger, db_session)
    pending_repo = PendingRegistrationRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.send_sms_verification_code.return_value = VerificationStatus.PENDING
    mock_ver.send_email_verification_code.return_value = VerificationStatus.APPROVED
    service = UserRegisterService(logger, repo, pending_repo, mock_ver)

    user_data = UserRegistrationRequest(
        first_name="Test",
        last_name="User",
        email="test3@example.com",
        date_of_birth="1990-01-01",
        zip_code="12345",
        address="123 Main St",
        race_id=1,
    )

    with pytest.raises(Exception) as excinfo:
        service.create_inactive_user(user_data)

    assert "email" in str(excinfo.value).lower()


def test_user_registration_rejects_both_email_and_phone() -> None:
    with pytest.raises(ValidationError, match="Cannot provide both"):
        UserRegistrationRequest(
            first_name="Test",
            last_name="User",
            email="test@example.com",
            phone_number="1234567890",
            date_of_birth="1990-01-01",
            zip_code="12345",
            address="123 Main St",
            race_id=1,
        )


def test_user_registration_requires_email_or_phone() -> None:
    with pytest.raises(ValidationError, match="At least one of"):
        UserRegistrationRequest(
            first_name="Test",
            last_name="User",
            date_of_birth="1990-01-01",
            zip_code="12345",
            address="123 Main St",
            race_id=1,
        )


def test_user_registration_treats_blank_email_as_missing_for_phone_flow() -> None:
    request = UserRegistrationRequest(
        first_name="Test",
        last_name="User",
        email="  ",
        phone_number="1234567890",
        date_of_birth="1990-01-01",
        zip_code="12345",
        address="123 Main St",
        race_id=1,
    )

    assert request.email is None
    assert request.phone_number == "1234567890"


def test_user_registration_treats_blank_phone_as_missing_for_email_flow() -> None:
    request = UserRegistrationRequest(
        first_name="Test",
        last_name="User",
        email="test@example.com",
        phone_number="  ",
        date_of_birth="1990-01-01",
        zip_code="12345",
        address="123 Main St",
        race_id=1,
    )

    assert request.email == "test@example.com"
    assert request.phone_number is None
