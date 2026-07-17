from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from logging import Logger, getLogger

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Constants.Constants import PENDING_REGISTRATION_EXPIRY_MINUTES
from src.Models.Base import Base
from src.Models.PendingRegistration import PendingRegistration
from src.Models.User import RaceLookup, User
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Utils.ExpiredRegistration import is_registration_expired
from src.Utils.Validators import ValidationError


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    SessionLocal = Session()

    SessionLocal.add(RaceLookup(race_id=1, description="Test Race"))
    SessionLocal.commit()

    test_users = [
        User(id="789021", email="user789021@example.com", race_id=1),
        User(id="919", email="user919@example.com", race_id=1),
        User(id="12", email="user12@example.com", race_id=1),
        User(id="13", email="user13@example.com", race_id=1),
    ]
    for user in test_users:
        SessionLocal.add(user)
    SessionLocal.commit()

    yield SessionLocal
    SessionLocal.close()


@pytest.fixture
def logger():
    return getLogger("pending_registration_test")


@pytest.fixture
def pending_registration_repo(logger: Logger, db_session: Session) -> PendingRegistrationRepository:
    return PendingRegistrationRepository(logger, db_session)


@pytest.fixture
def make_test_registration(db_session: Session):
    pendingReg = PendingRegistration(
        ID=str(uuid.uuid4()),
        USER_ID="789021",
    )
    db_session.add(pendingReg)
    db_session.commit()
    return pendingReg


@pytest.fixture
def make_test_registration_expired(db_session: Session):
    pendingReg = PendingRegistration(
        ID=str(uuid.uuid4()),
        USER_ID="789021",
    )
    # Making sure the registration should be expired by changing the creation time
    pendingReg.CREATED_AT = datetime.now() - timedelta(PENDING_REGISTRATION_EXPIRY_MINUTES * 2)

    db_session.add(pendingReg)
    db_session.commit()
    return pendingReg


@pytest.fixture
def make_test_registration_not_expired(db_session: Session) -> PendingRegistration:
    pendingReg = PendingRegistration(
        ID=str(uuid.uuid4()),
        USER_ID="789021",
    )
    db_session.add(pendingReg)
    db_session.commit()
    return pendingReg


@pytest.fixture
def make_test_registrations(db_session: Session):
    more_pending_regs = [
        PendingRegistration(
            ID=str(uuid.uuid4()),
            USER_ID="919",
        ),
        PendingRegistration(
            ID=str(uuid.uuid4()),
            USER_ID="12",
        ),
    ]
    for reg in more_pending_regs:
        db_session.add(reg)
    db_session.commit()
    return more_pending_regs


@pytest.fixture
def make_test_registrations_not_expired(db_session: Session) -> list[PendingRegistration]:
    more_pending_regs = [
        PendingRegistration(
            ID=str(uuid.uuid4()),
            USER_ID="919",
        ),
        PendingRegistration(
            ID=str(uuid.uuid4()),
            USER_ID="12",
        ),
    ]
    for reg in more_pending_regs:
        db_session.add(reg)
    db_session.commit()
    return more_pending_regs


@pytest.fixture
def make_test_registrations_mixed(db_session: Session):
    still_pending = PendingRegistration(
        ID=str(uuid.uuid4()),
        USER_ID="13",
    )
    db_session.add(still_pending)
    db_session.commit()
    return still_pending


@pytest.fixture
def make_unexpired_registration(db_session: Session):
    pending = PendingRegistration(
        ID="1234",
        USER_ID="789021",
    )
    db_session.add(pending)
    db_session.commit()
    return pending


def test_get_pending_registration_does_not_exist(
    pending_registration_repo: PendingRegistrationRepository,
):
    result = pending_registration_repo.get_registration_by_id("5")
    assert result is None


def test_get_pending_registration_success(
    pending_registration_repo: PendingRegistrationRepository,
    make_unexpired_registration: PendingRegistration,
):
    expected_result = make_unexpired_registration
    result = pending_registration_repo.get_registration_by_id(expected_result.ID)
    assert result is not None
    assert result.ID == expected_result.ID
    assert result.USER_ID == expected_result.USER_ID


def test_delete_by_id_success(
    pending_registration_repo: PendingRegistrationRepository,
    make_test_registration: PendingRegistration,
):
    result = pending_registration_repo.delete_registration_by_id(make_test_registration.ID)
    assert result is not None
    assert result == f"Successfully deleted {make_test_registration.ID} by id"


def test_delete_by_id_not_found(pending_registration_repo: PendingRegistrationRepository):
    result = pending_registration_repo.delete_registration_by_id("1")
    assert result is not None
    assert result == "pending registration not found"


def test_get_email_from_pending_registration_success(
    pending_registration_repo: PendingRegistrationRepository,
    make_test_registration_not_expired: PendingRegistration,
):
    result = pending_registration_repo.get_user_email_from_pending_registration(
        make_test_registration_not_expired.ID
    )
    assert result is not None


def test_get_email_from_pending_registration_not_found(
    pending_registration_repo: PendingRegistrationRepository,
):
    result = pending_registration_repo.get_user_email_from_pending_registration("1")
    assert result is None


def test_get_email_from_pending_registration_not_expired(
    pending_registration_repo: PendingRegistrationRepository,
    make_test_registrations_not_expired: list[PendingRegistration],
):
    result = pending_registration_repo.get_user_email_from_pending_registration(
        make_test_registrations_not_expired[0].ID
    )
    assert result is not None


def test_insert_pending_reg_no_new_email(pending_registration_repo: PendingRegistrationRepository):
    result: str = pending_registration_repo.insert_pending_registration(user_id="900")

    assert result is not None
    uuid.UUID(result)


def test_insert_pending_reg_with_new_email(
    pending_registration_repo: PendingRegistrationRepository,
):
    result = pending_registration_repo.insert_pending_registration(
        user_id="324872",
        new_email="newEmail@h4i.com",
    )

    assert result is not None
    uuid.UUID(result)


def test_invalid_email_insert(pending_registration_repo: PendingRegistrationRepository):
    with pytest.raises(ValidationError) as exc_info:
        pending_registration_repo.insert_pending_registration(
            user_id="234671",
            new_email="new email",
        )
    assert "Invalid email" in str(exc_info.value)


# --- get_registration_by_id ---


def test_get_registration_by_id_found(
    pending_registration_repo: PendingRegistrationRepository,
    make_test_registration: PendingRegistration,
):
    result = pending_registration_repo.get_registration_by_id(make_test_registration.ID)
    assert result is not None
    assert result.ID == make_test_registration.ID


def test_get_registration_by_id_returns_expired_records(
    pending_registration_repo: PendingRegistrationRepository,
    make_test_registration_expired: PendingRegistration,
):
    """Expired registrations should still be returned (no expiry filter)."""
    result = pending_registration_repo.get_registration_by_id(make_test_registration_expired.ID)
    assert result is not None
    assert is_registration_expired(result)


def test_get_registration_by_id_not_found(
    pending_registration_repo: PendingRegistrationRepository,
):
    result = pending_registration_repo.get_registration_by_id("nonexistent-id")
    assert result is None
