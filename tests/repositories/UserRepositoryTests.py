import logging
from collections.abc import Generator
from datetime import date
from logging import Logger
from typing import TypedDict, cast

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.DisplayUserRecord import DisplayUserRecord
from src.Models.User import Base, RaceLookup, User
from src.Repositories.UsersRepository import UsersRepository
from src.Utils.Validators import ValidationError

PAGINATED_PARENT_UUID = "dddddddd-dddd-dddd-dddd-dddddddddddd"
PAGINATED_CHILD_UUID = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"

RaceOption = tuple[int, str]


class UserPayload(TypedDict):
    first_name: str
    last_name: str
    email: str | None
    phone_number: str | None
    date_of_birth: str
    zip_code: str
    address: str
    race_id: int
    qr_token: str
    parent_id: str


# Fixtures
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
    return logging.getLogger("test_logger")


@pytest.fixture
def user_repo(logger: Logger, db_session: Session) -> UsersRepository:
    return UsersRepository(logger, db_session)


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
def test_user(db_session: Session) -> User:
    user = User(
        id=1,
        first_name="Jane",
        last_name="Smith",
        email="jane@gmail.com",
        phone_number="1234567890",
        date_of_birth=date(2000, 12, 12),
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
        qr_token="123",
        is_active=True,
        parent_id=None,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def valid_user_data() -> UserPayload:
    """Valid user data for testing add_user."""
    return cast(
        UserPayload,
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": None,
            "date_of_birth": "1990-01-01",
            "zip_code": "12345",
            "address": "123 Main St",
            "race_id": 1,
            "qr_token": "token123",
            "parent_id": None,
        },
    )


# Tests
def test_get_user_by_id(user_repo: UsersRepository, test_user: User) -> None:
    user = user_repo.get_user_by_id(test_user.id)

    assert user is not None
    assert user.id == test_user.id
    assert user.is_active is True
    assert user.first_name == "Jane"


def test_get_user_by_qr(user_repo: UsersRepository, test_user: User) -> None:
    assert test_user.qr_token is not None
    user = user_repo.get_user_by_qr(test_user.qr_token)
    assert user is not None
    assert user.qr_token == test_user.qr_token
    assert user.is_active is True


def test_attempt_get_inactive_user_by_qr(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    test_user.is_active = False
    db_session.commit()

    assert test_user.qr_token is not None
    user = user_repo.get_user_by_qr(test_user.qr_token)
    assert user is None


def test_get_user_then_delete_by_qr(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    assert test_user.qr_token is not None
    user = user_repo.get_user_by_qr(test_user.qr_token)
    assert user is not None
    assert user.qr_token == test_user.qr_token
    assert user.is_active is True

    user_repo.delete_user(user.id)
    db_session.commit()

    user = user_repo.get_user_by_qr(test_user.qr_token)
    assert user is None


def test_get_user_by_qr_not_found(user_repo: UsersRepository, test_user: User) -> None:
    user = user_repo.get_user_by_qr("qrtoken123")
    assert user is None


def test_get_user_by_email(user_repo: UsersRepository, test_user: User) -> None:
    assert test_user.email is not None
    user = user_repo.get_users_by_email(test_user.email)[0]
    assert user.email == test_user.email


def test_get_users_by_email_multiple(
    user_repo: UsersRepository, db_session: Session, test_user: User, valid_user_data: UserPayload
) -> None:
    assert test_user.email is not None
    valid_user_data["email"] = test_user.email
    valid_user_data["phone_number"] = None
    user2 = user_repo.add_user(**valid_user_data)
    db_session.commit()

    user_repo.set_active_status(user2, True)
    db_session.commit()

    users = user_repo.get_users_by_email(test_user.email)
    assert test_user.email is not None
    assert len(users) == 2


def test_get_users_by_email_then_delete(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    assert test_user.email is not None
    user = user_repo.get_users_by_email(test_user.email)[0]
    assert user != []
    assert user.email == test_user.email
    assert user.is_active is True

    user_repo.delete_user(user.id)
    db_session.commit()

    user = user_repo.get_users_by_email(test_user.email)
    assert user == []


def test_get_one_active_users(
    user_repo: UsersRepository, db_session: Session, test_user: User, valid_user_data: UserPayload
) -> None:
    assert test_user.email is not None
    valid_user_data["email"] = test_user.email
    valid_user_data["phone_number"] = None
    user_repo.add_user(**valid_user_data)  # this user hasn't been verified yet
    db_session.commit()

    users = user_repo.get_users_by_email(test_user.email)
    assert len(users) == 1


def test_get_users_by_email_all_inactive(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    assert test_user.email is not None
    test_user.is_active = False
    db_session.commit()

    users = user_repo.get_users_by_email(test_user.email)
    assert len(users) == 0


def test_get_user_by_email_not_found(user_repo: UsersRepository, test_user: User) -> None:
    users = user_repo.get_users_by_email(f"1{test_user.email}")

    assert len(users) == 0


def test_get_by_user_phone(user_repo: UsersRepository, test_user: User) -> None:
    assert test_user.phone_number is not None
    user = user_repo.get_users_by_phone_number("123-456-7890")[0]
    assert user.phone_number == test_user.phone_number


def test_get_users_by_phone_then_delete(
    user_repo: UsersRepository,
    db_session: Session,
    test_user: User,  # add db_session
) -> None:
    assert test_user.phone_number is not None
    user = user_repo.get_users_by_phone_number(test_user.phone_number)[0]
    assert user.phone_number == test_user.phone_number

    user_repo.delete_user(user.id)
    db_session.commit()

    users = user_repo.get_users_by_phone_number(test_user.phone_number)
    assert len(users) == 0


def test_get_one_active_out_of_two(
    user_repo: UsersRepository, db_session: Session, test_user: User, valid_user_data: UserPayload
) -> None:
    assert test_user.phone_number is not None
    valid_user_data["phone_number"] = test_user.phone_number
    valid_user_data["email"] = None
    user_repo.add_user(**valid_user_data)  # this user hasnt been vertified yet
    db_session.commit()

    users = user_repo.get_users_by_phone_number(test_user.phone_number)
    assert test_user.email is not None
    assert len(users) == 1


def test_get_users_by_phone_number_all_inactive(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    assert test_user.phone_number is not None
    test_user.is_active = False
    db_session.commit()

    users = user_repo.get_users_by_phone_number(test_user.phone_number)
    assert test_user.phone_number is not None
    assert len(users) == 0


def test_get_user_by_phone_number_not_found(user_repo: UsersRepository, test_user: User) -> None:
    users = user_repo.get_users_by_phone_number(f"1{test_user.phone_number}")

    assert len(users) == 0


def test_get_multiple_users(
    user_repo: UsersRepository, test_user: User, valid_user_data: UserPayload
) -> None:
    assert test_user.qr_token is not None
    user = user_repo.get_user_by_qr(test_user.qr_token)

    # adding the 2nd user
    user2 = user_repo.add_user(**valid_user_data)
    user_repo.set_active_status(user2, True)

    assert user2.qr_token is not None
    user2 = user_repo.get_user_by_qr(user2.qr_token)
    assert user is not None
    assert user2 is not None
    assert user != user2


def test_user_not_found(user_repo: UsersRepository) -> None:
    assert user_repo.get_user_by_id("999") is None


def test_set_inactive_and_commit(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    user_repo.set_active_status(test_user, False)
    db_session.commit()

    db_session.expire_all()
    user = user_repo.get_user_by_id(test_user.id)
    assert user is not None
    assert user.is_active is False


def test_rollback_discards_changes(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    user_repo.set_active_status(test_user, False)
    db_session.rollback()

    db_session.expire_all()
    user = user_repo.get_user_by_id(test_user.id)
    assert user is not None
    assert user.is_active is True


def test_soft_delete_twice(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    user_repo.set_active_status(test_user, False)
    db_session.commit()

    user_repo.set_active_status(test_user, False)
    db_session.commit()

    db_session.expire_all()
    user = user_repo.get_user_by_id(test_user.id)
    assert user is not None
    assert user.is_active is False


def test_delete_user_successful(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    result = user_repo.delete_user(test_user.id)
    db_session.commit()

    assert result == "deleted"
    db_session.expire_all()
    user = user_repo.get_user_by_id(test_user.id)
    assert user is not None
    assert user.is_active is False


def test_delete_user_not_found(user_repo: UsersRepository) -> None:
    result = user_repo.delete_user("999")
    assert result == "user_not_found"


def test_delete_user_already_deleted(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    user_repo.delete_user(test_user.id)
    db_session.commit()

    result = user_repo.delete_user(test_user.id)
    assert result == "already_deleted"


def test_extract_races(
    user_repo: UsersRepository, db_session: Session, test_race_lookup: list[RaceOption]
) -> None:
    lst = user_repo.get_all_races_from_db()
    assert lst == test_race_lookup, "Race lists should be equal"


def test_extract_races_fail(user_repo: UsersRepository, db_session: Session) -> None:
    lst = user_repo.get_all_races_from_db()
    assert lst is None, "List when extracting races should None"


def test_add_user(user_repo: UsersRepository, db_session: Session) -> None:
    valid_data = cast(
        UserPayload,
        {
            "first_name": "John",
            "last_name": "Doe",
            "email": "john.doe@example.com",
            "phone_number": None,
            "date_of_birth": "1990-01-01",
            "zip_code": "12345",
            "address": "123 Main St",
            "race_id": 1,
            "qr_token": "token123",
            "parent_id": None,
        },
    )

    user = user_repo.add_user(**valid_data)
    db_session.commit()

    assert isinstance(user.id, str)

    fetched = user_repo.get_user_by_id(user.id)

    assert fetched is not None
    assert fetched.id is not None
    assert fetched.first_name == "John"
    assert fetched.last_name == "Doe"
    assert fetched.email == "john.doe@example.com"
    assert fetched.date_of_birth == date(1990, 1, 1)
    assert fetched.is_active is False


def test_add_same_email(
    user_repo: UsersRepository, db_session: Session, valid_user_data: UserPayload
) -> None:
    user = user_repo.add_user(**valid_user_data)
    db_session.commit()

    child_user_data: UserPayload = {**valid_user_data, "qr_token": "token111"}
    child_user = user_repo.add_user(**child_user_data)
    db_session.commit()

    assert isinstance(user.id, str)
    assert isinstance(child_user.id, str)
    fetched_user = user_repo.get_user_by_id(user.id)
    fetched_child_user = user_repo.get_user_by_id(child_user.id)

    assert fetched_user is not None
    assert fetched_child_user is not None
    assert fetched_child_user.id is not None
    assert fetched_user.email == "john.doe@example.com"
    assert fetched_child_user.email == "john.doe@example.com"
    assert fetched_child_user.is_active is False


def test_add_same_phone_number(
    user_repo: UsersRepository, db_session: Session, valid_user_data: UserPayload
) -> None:
    valid_user_data["email"] = None
    valid_user_data["phone_number"] = "123-456-7890"

    user = user_repo.add_user(**valid_user_data)
    db_session.commit()

    child_user_data: UserPayload = {**valid_user_data, "qr_token": "token111"}
    child_user = user_repo.add_user(**child_user_data)
    db_session.commit()

    assert isinstance(user.id, str)
    assert isinstance(child_user.id, str)
    fetched_user = user_repo.get_user_by_id(user.id)
    fetched_child_user = user_repo.get_user_by_id(child_user.id)

    assert fetched_user is not None
    assert fetched_child_user is not None
    assert fetched_child_user.id is not None
    assert fetched_user.phone_number == "1234567890"
    assert fetched_child_user.phone_number == "1234567890"  # cleaned number inserted in the db
    assert fetched_child_user.is_active is False


# Validation Tests
def test_add_user_missing_first_name(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["first_name"] = ""

    with pytest.raises(ValidationError, match="is required"):
        user_repo.add_user(**valid_user_data)


def test_add_user_missing_last_name(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["last_name"] = ""

    with pytest.raises(ValidationError, match="is required"):
        user_repo.add_user(**valid_user_data)


def test_add_user_first_name_only_spaces(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["first_name"] = "  "

    with pytest.raises(ValidationError, match="is required"):
        user_repo.add_user(**valid_user_data)


def test_add_user_missing_contact(user_repo: UsersRepository, valid_user_data: UserPayload) -> None:
    valid_user_data["email"] = ""

    with pytest.raises(ValidationError, match="Either email or phone_number is required"):
        user_repo.add_user(**valid_user_data)


def test_add_user_rejects_both_email_and_phone(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["phone_number"] = "123-456-7890"

    with pytest.raises(ValidationError, match="Cannot provide both"):
        user_repo.add_user(**valid_user_data)


def test_add_user_invalid_email_format(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["email"] = "john.doeexamplecom"

    with pytest.raises(ValidationError, match="Invalid email"):
        user_repo.add_user(**valid_user_data)


def test_add_user_phone_number_too_long(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["email"] = None
    valid_user_data["phone_number"] = "267111111111111111"

    with pytest.raises(ValidationError, match="Phone number"):
        user_repo.add_user(**valid_user_data)


def test_add_user_phone_number_too_short(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["email"] = None
    valid_user_data["phone_number"] = "267"

    with pytest.raises(ValidationError, match="Phone number"):
        user_repo.add_user(**valid_user_data)


def test_add_user_phone_number_with_letters(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["email"] = None
    valid_user_data["phone_number"] = "267a121234"

    with pytest.raises(ValidationError, match="Phone number"):
        user_repo.add_user(**valid_user_data)


def test_add_user_invalid_date_format(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["date_of_birth"] = "120320032"

    with pytest.raises(ValidationError, match="Date of birth"):
        user_repo.add_user(**valid_user_data)


def test_add_user_future_date_of_birth(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["date_of_birth"] = "2999-12-31"

    with pytest.raises(ValidationError, match="Date of birth"):
        user_repo.add_user(**valid_user_data)


def test_add_user_invalid_date_value(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["date_of_birth"] = "1990-13-45"

    with pytest.raises(ValidationError, match="Date of birth"):
        user_repo.add_user(**valid_user_data)


def test_add_user_zipcode_with_letters(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["zip_code"] = "1915a"

    with pytest.raises(ValidationError, match="Zip code"):
        user_repo.add_user(**valid_user_data)


def test_add_user_zipcode_too_short(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["zip_code"] = "1"

    with pytest.raises(ValidationError, match="Zip code"):
        user_repo.add_user(**valid_user_data)


def test_add_user_zipcode_too_long(
    user_repo: UsersRepository, valid_user_data: UserPayload
) -> None:
    valid_user_data["zip_code"] = "2134512345"

    with pytest.raises(ValidationError, match="Zip code"):
        user_repo.add_user(**valid_user_data)


def test_add_user_duplicate_qr_token(
    user_repo: UsersRepository, db_session: Session, test_user: User
) -> None:
    duplicate_data = cast(
        UserPayload,
        {
            "first_name": "Another",
            "last_name": "User",
            "email": "unique@example.com",
            "phone_number": None,
            "date_of_birth": "1995-01-01",
            "zip_code": "12345",
            "address": "456 Oak St",
            "race_id": 1,
            "qr_token": test_user.qr_token,
            "parent_id": None,
        },
    )

    with pytest.raises(ValidationError, match="QR token already exists"):
        user_repo.add_user(**duplicate_data)
        db_session.commit()


def test_race_lookup_returns_string(
    user_repo: UsersRepository,
    test_user: User,
    db_session: Session,
    test_race_lookup: list[RaceOption],
) -> None:
    race = user_repo.get_race(test_user.id, test_user.race_id)
    assert race == "White"


@pytest.fixture
def paginated_parent(db_session: Session) -> User:
    user = User(
        id=PAGINATED_PARENT_UUID,
        first_name="Alice",
        last_name="Walker",
        email="alice@example.com",
        phone_number="5550001111",
        date_of_birth=date(1980, 5, 20),
        zip_code="19103",
        address="1 Penn Sq",
        race_id=1,
        qr_token="paginated-parent-qr",
        is_active=True,
        parent_id=None,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def paginated_child(db_session: Session, paginated_parent: User) -> User:
    user = User(
        id=PAGINATED_CHILD_UUID,
        first_name="Charlie",
        last_name="Walker",
        email="alice@example.com",
        phone_number="5550001111",
        date_of_birth=date(2012, 3, 10),
        zip_code="19103",
        address="1 Penn Sq",
        race_id=2,
        qr_token="paginated-child-qr",
        is_active=True,
        parent_id=PAGINATED_PARENT_UUID,
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_get_users_paginated_returns_display_user_records(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=10)

    assert len(results) == 1
    assert isinstance(results[0], DisplayUserRecord)


def test_get_users_paginated_resolves_race_description(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=10)

    assert results[0].race_description == "White"


def test_get_users_paginated_top_level_user_has_null_parent_names(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=10)

    assert results[0].parent_first_name is None
    assert results[0].parent_last_name is None


def test_get_users_paginated_child_resolves_parent_names(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
    paginated_child: User,
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=10)
    child_record = next(r for r in results if r.first_name == "Charlie")

    assert child_record.parent_first_name == "Alice"
    assert child_record.parent_last_name == "Walker"


def test_get_users_paginated_maps_user_fields(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=10)
    record = results[0]

    assert record.first_name == paginated_parent.first_name
    assert record.last_name == paginated_parent.last_name
    assert record.email == paginated_parent.email
    assert record.is_active == paginated_parent.is_active
    assert (
        record.date_of_birth == paginated_parent.date_of_birth.strftime("%Y-%m-%d")
        if paginated_parent.date_of_birth
        else None
    )


def test_get_users_paginated_respects_page_size(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
    paginated_child: User,
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=1)

    assert len(results) == 1


def test_get_users_paginated_second_page_returns_next_record(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
    paginated_parent: User,
    paginated_child: User,
) -> None:
    page1 = user_repo.get_users_paginated(page=1, page_size=1)
    page2 = user_repo.get_users_paginated(page=2, page_size=1)

    assert len(page1) == 1
    assert len(page2) == 1
    assert page1[0].first_name != page2[0].first_name


def test_get_users_paginated_empty_returns_empty_list(
    user_repo: UsersRepository,
    test_race_lookup: list[RaceOption],
) -> None:
    results = user_repo.get_users_paginated(page=1, page_size=10)

    assert results == []
