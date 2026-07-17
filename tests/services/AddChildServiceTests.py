from __future__ import annotations

from collections.abc import Generator
from logging import Logger, getLogger
from typing import cast
from unittest.mock import Mock

import pytest
from sqlalchemy import Table, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.Models.exceptions import NotFoundException
from src.Models.User import RaceLookup, User
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.AddChildRequest import AddChildRequest
from src.Services.AccountService import AccountService
from src.Services.VerificationService import VerificationService, VerificationStatus
from src.Utils.Validators import ValidationError


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    cast(Table, RaceLookup.__table__).create(engine, checkfirst=True)

    with engine.connect() as conn:
        conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone_number TEXT,
                date_of_birth DATE,
                zip_code TEXT,
                address TEXT,
                race_id INTEGER NOT NULL REFERENCES "Race_Lookup" (race_id),
                qr_token TEXT UNIQUE,
                is_active BOOLEAN NOT NULL,
                parent_id TEXT REFERENCES users (id),
                created_at DATETIME,
                updated_at DATETIME
            )
        """)
        )
        conn.commit()

    Session = sessionmaker(bind=engine)
    session = Session()

    race = RaceLookup(race_id=1, description="Test Race")
    session.add(race)
    session.commit()

    yield session
    session.close()


@pytest.fixture
def logger() -> Logger:
    return getLogger("test_logger")


@pytest.fixture
def mock_verification_service() -> VerificationService:
    mock_verification = Mock()
    mock_verification.send_sms_verification_code.return_value = VerificationStatus.PENDING
    mock_verification.send_email_verification_code.return_value = VerificationStatus.PENDING
    return mock_verification


@pytest.fixture
def account_service(
    logger: Logger, db_session: Session, mock_verification_service: VerificationService
) -> AccountService:
    pending_repo = PendingRegistrationRepository(logger, db_session)
    users_repo = UsersRepository(logger, db_session)
    return AccountService(logger, pending_repo, users_repo, mock_verification_service)


@pytest.fixture
def active_parent(db_session: Session) -> User:
    parent = User(
        id="550e8400-e29b-41d4-a716-446655440000",
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone_number=None,
        zip_code="19104",
        address="123 Main St",
        race_id=1,
        qr_token="parent-qr-token",
        is_active=True,
        parent_id=None,
    )
    db_session.add(parent)
    db_session.commit()
    return parent


@pytest.fixture
def inactive_parent(db_session: Session) -> User:
    parent = User(
        id="660e8400-e29b-41d4-a716-446655440000",
        first_name="Bob",
        last_name="Smith",
        email=None,
        phone_number="2159999999",
        zip_code="19104",
        address="456 Elm St",
        race_id=1,
        qr_token="inactive-qr-token",
        is_active=False,
        parent_id=None,
    )
    db_session.add(parent)
    db_session.commit()
    return parent


@pytest.fixture
def child_request() -> AddChildRequest:
    return AddChildRequest(
        parent_id="550e8400-e29b-41d4-a716-446655440000",
        first_name="Kid",
        last_name="Doe",
        date_of_birth="2015-06-01",
        zip_code="19104",
        address="123 Main St",
        race_id=1,
    )


def test_add_child_success(
    account_service: AccountService,
    db_session: Session,
    active_parent: User,
    child_request: AddChildRequest,
) -> None:
    result = account_service.add_child(child_request)

    assert result.first_name == "Kid"
    assert result.last_name == "Doe"
    assert result.email == active_parent.email
    assert result.phone_number is None
    assert result.parent_id == active_parent.id
    assert result.qr_token is not None


def test_add_child_inherits_parent_contact_info(
    account_service: AccountService,
    db_session: Session,
    active_parent: User,
    child_request: AddChildRequest,
) -> None:
    result = account_service.add_child(child_request)

    assert result.email == "jane@example.com"
    assert result.phone_number is None


def test_add_child_is_active(
    account_service: AccountService,
    db_session: Session,
    active_parent: User,
    child_request: AddChildRequest,
) -> None:
    result = account_service.add_child(child_request)

    child = db_session.get(User, result.id)
    assert child is not None
    assert child.is_active is True


def test_add_child_parent_not_found(
    account_service: AccountService,
    child_request: AddChildRequest,
) -> None:
    child_request.parent_id = "770e8400-e29b-41d4-a716-446655440000"

    with pytest.raises(NotFoundException):
        account_service.add_child(child_request)


def test_add_child_parent_inactive(
    account_service: AccountService,
    inactive_parent: User,
    child_request: AddChildRequest,
) -> None:
    child_request.parent_id = inactive_parent.id

    with pytest.raises(NotFoundException):
        account_service.add_child(child_request)


def test_add_child_qr_token_unique(
    account_service: AccountService,
    db_session: Session,
    active_parent: User,
    child_request: AddChildRequest,
) -> None:
    result1 = account_service.add_child(child_request)

    child_request2 = AddChildRequest(
        parent_id="550e8400-e29b-41d4-a716-446655440000",
        first_name="Kid2",
        last_name="Doe",
        date_of_birth="2017-03-15",
        zip_code="19104",
        address="123 Main St",
        race_id=1,
    )
    result2 = account_service.add_child(child_request2)

    assert result1.qr_token != result2.qr_token


def test_add_child_invalid_parent_id(
    account_service: AccountService,
    child_request: AddChildRequest,
) -> None:
    child_request.parent_id = "not-a-uuid"

    with pytest.raises(ValidationError):
        account_service.add_child(child_request)
