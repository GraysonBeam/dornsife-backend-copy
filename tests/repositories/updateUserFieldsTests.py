from __future__ import annotations

import logging
from collections.abc import Generator
from logging import getLogger
from typing import cast

import pytest
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.Base import Base
from src.Models.User import RaceLookup, User
from src.Repositories.UsersRepository import UsersRepository
from src.Utils.Validators import ValidationError

logging.basicConfig(level=logging.INFO)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    user_table = cast(Table, User.__table__)
    race_lookup_table = cast(Table, RaceLookup.__table__)
    Base.metadata.create_all(engine, tables=[user_table, race_lookup_table])
    SessionLocal = sessionmaker(bind=engine)()

    races = [
        RaceLookup(race_id=1, description="White"),
        RaceLookup(race_id=2, description="Asian"),
    ]
    for r in races:
        SessionLocal.add(r)

    users = [
        User(
            id=1,
            first_name="Alice",
            last_name="Smith",
            email="alice@example.com",
            phone_number="2151110000",
            zip_code="19104",
            address="123 Main St",
            race_id=1,
            is_active=True,
        ),
        User(
            id=2,
            first_name="Bob",
            last_name="Jones",
            email="bob@example.com",
            phone_number="2152220000",
            zip_code="19103",
            address="456 Elm St",
            race_id=1,
            is_active=False,
        ),
    ]
    for u in users:
        SessionLocal.add(u)
    SessionLocal.commit()

    yield SessionLocal
    SessionLocal.close()


@pytest.fixture
def users_repo(db_session: Session) -> UsersRepository:
    return UsersRepository(getLogger("test"), db_session)


def test_update_single_field(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="1", first_name="Alicia")
    assert result == "success"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.first_name == "Alicia"
    assert user.last_name == "Smith"  # unchanged


def test_update_multiple_fields(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="1", first_name="Alicia", zip_code="19107")
    assert result == "success"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.first_name == "Alicia"
    assert user.zip_code == "19107"
    assert user.email == "alice@example.com"  # unchanged


def test_null_fields_not_overwritten(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="1", first_name=None, last_name="Updated")
    assert result == "success"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.first_name == "Alice"  # null ignored
    assert user.last_name == "Updated"


def test_no_fields_provided(users_repo: UsersRepository) -> None:
    result = users_repo.update_user_fields(user_id="1")
    assert result == "no_fields_provided"


def test_user_not_found(users_repo: UsersRepository) -> None:
    result = users_repo.update_user_fields(user_id="9999", first_name="Ghost")
    assert result == "user_not_found"


def test_inactive_user_rejected(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="2", first_name="Bobby")
    assert result == "user_inactive"
    user = db_session.get(User, 2)
    assert user is not None
    assert user.first_name == "Bob"


def test_update_phone_number(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="1", phone_number="2159999999")
    assert result == "success"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.email is None
    assert user.phone_number == "2159999999"


def test_update_email_clears_phone_number(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="1", email="newalice@example.com")
    assert result == "success"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.email == "newalice@example.com"
    assert user.phone_number is None


def test_update_rejects_both_email_and_phone_number(users_repo: UsersRepository) -> None:
    with pytest.raises(ValidationError, match="Cannot provide both"):
        users_repo.update_user_fields(
            user_id="1", email="newalice@example.com", phone_number="2159999999"
        )


def test_blank_email_update_is_treated_as_not_provided(
    users_repo: UsersRepository, db_session: Session
) -> None:
    result = users_repo.update_user_fields(user_id="1", email="   ")
    assert result == "no_fields_provided"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.phone_number == "2151110000"


def test_blank_phone_update_is_treated_as_not_provided(
    users_repo: UsersRepository, db_session: Session
) -> None:
    result = users_repo.update_user_fields(user_id="1", phone_number="   ")
    assert result == "no_fields_provided"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.email == "alice@example.com"
    assert user.phone_number == "2151110000"


def test_update_race_id(users_repo: UsersRepository, db_session: Session) -> None:
    result = users_repo.update_user_fields(user_id="1", race_id=2)
    assert result == "success"
    user = db_session.get(User, 1)
    assert user is not None
    assert user.race_id == 2
