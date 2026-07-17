from collections import defaultdict
from collections.abc import Generator
from datetime import date
from logging import Logger, getLogger
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.AccountActivation import AccountActivation, ActivationType
from src.Models.Base import Base
from src.Models.DisplayUserRecord import DisplayUserRecord
from src.Models.exceptions import NotFoundException
from src.Models.PendingRegistration import PendingRegistration
from src.Models.User import RaceLookup, User
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.AddChildRequest import AddChildRequest
from src.Services.AccountService import AccountService
from src.Services.VerificationService import VerificationStatus
from src.Utils.Validators import ValidationError

RaceOption = tuple[int, str]


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    SessionLocal = Session()
    yield SessionLocal
    SessionLocal.close()


@pytest.fixture
def logger() -> Logger:
    return getLogger("test_logger")


@pytest.fixture
def test_users(db_session: Session) -> list[User]:
    users = [
        User(
            id="1",
            first_name="Jane",
            last_name="Smith",
            email="jane@gmail.com",
            phone_number=None,
            date_of_birth=date(2000, 12, 12),
            zip_code="12345",
            address="3675 Market St",
            race_id=1,
            qr_token="123",
            is_active=True,
            parent_id=None,
        ),
        User(
            id=2,
            first_name="Bill",
            last_name="Bot",
            email=None,
            phone_number="223-456-7890",
            date_of_birth=date(2001, 12, 12),
            zip_code="12345",
            address="3675 Market St",
            race_id=1,
            qr_token="1234",
            is_active=False,
            parent_id=None,
        ),
    ]
    for user in users:
        db_session.add(user)
        db_session.commit()
    return users


@pytest.fixture
def test_pending_registrations(db_session: Session) -> list[PendingRegistration]:
    registrations = [
        PendingRegistration(
            ID="1234567890",
            USER_ID="1",
        ),
        PendingRegistration(
            ID="1672392",
            USER_ID="123",
        ),
        PendingRegistration(
            ID="13236767",
            USER_ID=2,
            NEW_EMAIL="billb@h4i.com",
        ),
    ]
    for registration in registrations:
        db_session.add(registration)
        db_session.commit()
    return registrations


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

    for _id, race_name in mock_race_table.items():
        race_obj = RaceLookup(race_id=_id, description=race_name)
        db_session.add(race_obj)
        db_session.commit()
        race_lst.append((race_obj.race_id, race_obj.description))  # Changed to tuple

    return race_lst


@pytest.fixture
def test_pending_reg_repo(logger: Logger, db_session: Session) -> PendingRegistrationRepository:
    return PendingRegistrationRepository(logger, db_session)


@pytest.fixture
def test_account_service(
    logger: Logger, db_session: Session, test_pending_reg_repo: PendingRegistrationRepository
) -> AccountService:
    usersRepo = UsersRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = True
    mock_ver.verify_verification_code_email.return_value = True
    return AccountService(logger, test_pending_reg_repo, usersRepo, mock_ver)


def test_account_activation_success(
    test_account_service: AccountService,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    activation: AccountActivation = test_account_service.process_account_activation(
        id="1234567890", verification_code="A", verification_type="email"
    )
    assert activation is not None
    assert activation.uuid == "1"
    assert activation.qr_token == "123"
    assert activation.type == ActivationType.NEW_ACCOUNT


def test_non_existant_registration_activation_failure(
    logger: Logger,
    db_session: Session,
    test_pending_reg_repo: PendingRegistrationRepository,
    test_account_service: AccountService,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    usersRepo = UsersRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = True
    mock_ver.verify_verification_code_email.return_value = False
    service = AccountService(logger, test_pending_reg_repo, usersRepo, mock_ver)
    with pytest.raises(NotFoundException) as error_info:
        service.process_account_activation("5", "123", "email")

    assert "not found" in str(error_info.value)


def test_expired_registration_fails(
    logger: Logger,
    db_session: Session,
    test_pending_reg_repo: PendingRegistrationRepository,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    usersRepo = UsersRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = False
    mock_ver.verify_verification_code_email.return_value = False
    service = AccountService(logger, test_pending_reg_repo, usersRepo, mock_ver)
    pending_reg = test_pending_registrations[0]
    with pytest.raises(ValidationError) as error_info:
        service.process_account_activation(pending_reg.ID, "123456", "email")

    assert "Failed" in str(error_info.value)


def test_activation_success_deletes_pending_reg(
    logger: Logger,
    db_session: Session,
    test_pending_reg_repo: PendingRegistrationRepository,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    usersRepo = UsersRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = True
    mock_ver.verify_verification_code_email.return_value = True
    service = AccountService(logger, test_pending_reg_repo, usersRepo, mock_ver)
    activation: AccountActivation = service.process_account_activation(
        id="1234567890", verification_code="A", verification_type="email"
    )
    assert activation is not None
    assert activation.uuid == "1"
    assert activation.qr_token == "123"
    record_left = test_pending_reg_repo.delete_registration_by_id("1234567890")
    assert record_left is not None
    assert "pending registration not found" in record_left


def test_update_email_path_success(
    test_account_service: AccountService,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
    test_pending_reg_repo: PendingRegistrationRepository,
):
    activation: AccountActivation = test_account_service.process_account_activation(
        id=test_pending_registrations[2].ID, verification_code="123456", verification_type="sms"
    )
    assert activation.uuid == "2"
    assert activation.qr_token == "1234"
    assert activation.type == ActivationType.UPDATE_EMAIL


def test_get_user_profiles_by_uuid(
    test_account_service: AccountService,
    test_race_lookup: list[RaceOption],
    db_session: Session,
    test_users: list[User],
):
    res = test_account_service.get_user_profile_by_uuid("1")

    mock_dict: defaultdict[str, str] = defaultdict[str, str](str)
    mock_dict["first_name"] = test_users[0].first_name or ""
    mock_dict["last_name"] = test_users[0].last_name or ""
    mock_dict["email"] = test_users[0].email or ""
    mock_dict["phone_number"] = test_users[0].phone_number or ""
    if test_users[0].date_of_birth is not None:
        mock_dict["date_of_birth"] = test_users[0].date_of_birth.strftime("%Y-%m-%d")
    else:
        mock_dict["date_of_birth"] = ""
    mock_dict["zip_code"] = test_users[0].zip_code or ""
    mock_dict["address"] = test_users[0].address or ""
    mock_dict["race"] = test_account_service.usersRepository.get_race(
        test_users[0].id, test_users[0].race_id
    )

    assert res == mock_dict


def test_update_user_profile_non_email_fields(
    test_account_service: AccountService,
    test_users: list[User],
    test_race_lookup: list[RaceOption],
):
    result = test_account_service.update_user_profile(
        uuid="1",
        first_name="Janet",
        zip_code="99999",
    )
    assert result["message"] == "Profile updated successfully."
    assert result["first_name"] == "Janet"
    assert result["zip_code"] == "99999"
    assert result.get("pending_registration_id") is None


def test_update_user_profile_email_creates_pending_registration(
    test_account_service: AccountService,
    test_users: list[User],
    test_pending_reg_repo: PendingRegistrationRepository,
    db_session: Session,
):
    from unittest.mock import MagicMock

    test_account_service.verificationService = MagicMock()
    test_account_service.verificationService.send_email_verification_code.return_value = (
        VerificationStatus.PENDING
    )

    result = test_account_service.update_user_profile(
        uuid="1",
        email="newemail@example.com",
    )

    assert "pending_registration_id" in result
    assert result["pending_registration_id"] is not None

    # Confirm the pending registration was actually persisted with the right email
    from src.Models.PendingRegistration import PendingRegistration

    pending_reg_id: str = result["pending_registration_id"]
    pending_reg = db_session.get(PendingRegistration, pending_reg_id)
    assert pending_reg is not None
    assert pending_reg.NEW_EMAIL == "newemail@example.com"

    # Confirm the email send was actually called
    test_account_service.verificationService.send_email_verification_code.assert_called_once()


def test_update_account_with_email_clears_phone_number(
    test_account_service: AccountService, test_users: list[User]
):
    user = test_users[1]

    activation = test_account_service.update_account_with_email(user, "newemail@example.com")

    assert activation.type == ActivationType.UPDATE_EMAIL
    assert user.email == "newemail@example.com"
    assert user.phone_number is None


def test_update_account_with_phone_number_clears_email(
    test_account_service: AccountService, test_users: list[User]
):
    user = test_users[0]

    activation = test_account_service.update_account_with_phone_number(user, "123-456-7890")

    assert activation.type == ActivationType.UPDATE_PHONE_NUMBER
    assert user.email is None
    assert user.phone_number == "1234567890"


def test_update_user_profile_inactive_user_raises_not_found(
    test_account_service: AccountService,
    test_users: list[User],
):
    with pytest.raises(NotFoundException):
        test_account_service.update_user_profile(
            uuid="2",
            first_name="Ghost",
        )


PARENT_UUID = "12345678-1234-5678-1234-567812345678"
INACTIVE_UUID = "87654321-4321-8765-4321-876543218765"
NO_CONTACT_UUID = "11111111-1111-1111-1111-111111111111"
NOT_FOUND_UUID = "99999999-9999-9999-9999-999999999999"


def test_add_child_success(
    test_account_service: AccountService,
    test_race_lookup: list[RaceOption],
    db_session: Session,
):
    parent = User(
        id=PARENT_UUID,
        first_name="Jane",
        last_name="Smith",
        email="jane@gmail.com",
        phone_number=None,
        date_of_birth=date(2000, 12, 12),
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
        qr_token="active-parent-token",
        is_active=True,
        parent_id=None,
    )
    db_session.add(parent)
    db_session.commit()

    request = AddChildRequest(
        parent_id=PARENT_UUID,
        first_name="Tommy",
        last_name="Smith",
        date_of_birth="2015-06-01",
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
    )
    response = test_account_service.add_child(request)
    assert response is not None
    assert response.first_name == "Tommy"
    assert response.parent_id == PARENT_UUID


def test_add_child_parent_not_found(
    test_account_service: AccountService,
    db_session: Session,
):
    request = AddChildRequest(
        parent_id=NOT_FOUND_UUID,
        first_name="Tommy",
        last_name="Smith",
        date_of_birth="2015-06-01",
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
    )
    with pytest.raises(NotFoundException) as error_info:
        test_account_service.add_child(request)
    assert "not found" in str(error_info.value)


def test_add_child_parent_inactive(
    test_account_service: AccountService,
    db_session: Session,
):
    parent = User(
        id=INACTIVE_UUID,
        first_name="Bill",
        last_name="Bot",
        email=None,
        phone_number="223-456-7890",
        date_of_birth=date(2001, 12, 12),
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
        qr_token="inactive-token",
        is_active=False,
        parent_id=None,
    )
    db_session.add(parent)
    db_session.commit()

    request = AddChildRequest(
        parent_id=INACTIVE_UUID,
        first_name="Tommy",
        last_name="Smith",
        date_of_birth="2015-06-01",
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
    )
    with pytest.raises(NotFoundException) as error_info:
        test_account_service.add_child(request)
    assert "not active" in str(error_info.value)


def test_add_child_parent_missing_contact(
    test_account_service: AccountService,
    db_session: Session,
    test_race_lookup: list[RaceOption],
):
    parent = User(
        id=NO_CONTACT_UUID,
        first_name="No",
        last_name="Contact",
        email=None,
        phone_number=None,
        date_of_birth=date(1990, 1, 1),
        zip_code="12345",
        address="123 Main St",
        race_id=1,
        qr_token="no-contact-token",
        is_active=True,
        parent_id=None,
    )
    db_session.add(parent)
    db_session.commit()

    request = AddChildRequest(
        parent_id=NO_CONTACT_UUID,
        first_name="Tommy",
        last_name="Smith",
        date_of_birth="2015-06-01",
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
    )
    with pytest.raises(NotFoundException) as error_info:
        test_account_service.add_child(request)
    assert "missing email or phone" in str(error_info.value)


def _make_display_record(
    first_name: str | None = "Dana",
    last_name: str | None = "Lee",
    email: str | None = "dana@example.com",
    phone_number: str | None = "5551112222",
    date_of_birth: str | None = "1975-08-14",
    zip_code: str | None = "19103",
    address: str | None = "2 Market St",
    race_description: str | None = "White",
    is_active: bool = True,
    parent_first_name: str | None = None,
    parent_last_name: str | None = None,
) -> DisplayUserRecord:
    return DisplayUserRecord(
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone_number=phone_number,
        date_of_birth=date_of_birth,
        zip_code=zip_code,
        address=address,
        race_description=race_description,
        is_active=is_active,
        parent_first_name=parent_first_name,
        parent_last_name=parent_last_name,
    )


def test_get_users_paginated_delegates_to_repository(
    logger: Logger,
    test_pending_reg_repo: PendingRegistrationRepository,
):
    from unittest.mock import MagicMock

    mock_repo = MagicMock()
    records = [_make_display_record(), _make_display_record(first_name="Sam")]
    mock_repo.get_users_paginated.return_value = records

    service = AccountService(logger, test_pending_reg_repo, mock_repo, Mock())
    results = service.get_users_paginated(page=1, page_size=10)

    mock_repo.get_users_paginated.assert_called_once_with(1, 10)
    assert results == records


def test_get_users_paginated_returns_display_user_records(
    logger: Logger,
    test_pending_reg_repo: PendingRegistrationRepository,
):
    from unittest.mock import MagicMock

    mock_repo = MagicMock()
    mock_repo.get_users_paginated.return_value = [_make_display_record(), _make_display_record()]

    service = AccountService(logger, test_pending_reg_repo, mock_repo, Mock())
    results = service.get_users_paginated(page=1, page_size=10)

    assert len(results) == 2
    assert all(isinstance(r, DisplayUserRecord) for r in results)


def test_get_users_paginated_empty_repo_returns_empty_list(
    logger: Logger,
    test_pending_reg_repo: PendingRegistrationRepository,
):
    from unittest.mock import MagicMock

    mock_repo = MagicMock()
    mock_repo.get_users_paginated.return_value = []

    service = AccountService(logger, test_pending_reg_repo, mock_repo, Mock())
    results = service.get_users_paginated(page=1, page_size=10)

    assert results == []
