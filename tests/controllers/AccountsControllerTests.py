import os
from collections import defaultdict
from datetime import date
from logging import Logger, getLogger
from typing import Any, cast
from uuid import uuid4

os.environ["VERIFICATION_TTL"] = "1440"

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Controllers.AccountsController import get_account_service
from src.Models.AccountActivation import ActivationType
from src.Models.Base import Base
from src.Models.DisplayUserRecord import DisplayUserRecord
from src.Models.PendingRegistration import PendingRegistration
from src.Models.User import RaceLookup, User
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Services.AccountService import AccountService


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        # removes the checker because the test client intance is running on a diff thread
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def logger():
    return getLogger()


@pytest.fixture
def test_user_repo(logger: Logger, db_session: Session):
    return UsersRepository(logger, db_session)


@pytest.fixture
def test_pending_repo(logger: Logger, db_session: Session):
    return PendingRegistrationRepository(logger, db_session)


@pytest.fixture
def test_race_lookup(db_session: Session):
    mock_race_table = {
        1: "White",
        2: "Black or African American",
        3: "American Indian or Alaska Native",
        4: "Native Hawaiian Or Pacific Islander",
        5: "Hispanic or Latino",
        6: "Other",
    }

    race_lst: list[tuple[int, str]] = []

    for _id, race_name in mock_race_table.items():
        race_obj = RaceLookup(race_id=_id, description=race_name)
        db_session.add(race_obj)
        db_session.commit()
        race_lst.append((race_obj.race_id, race_obj.description))  # Changed to tuple

    return race_lst


@pytest.fixture
def test_users(db_session: Session):
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
            qr_token="123465",
            is_active=False,
            parent_id=None,
        ),
    ]
    for user in users:
        db_session.add(user)
        db_session.commit()
    return users


@pytest.fixture
def test_pending_registrations(db_session: Session):
    registrations = [
        PendingRegistration(
            ID=str(uuid4()),
            USER_ID=1,
        ),
        PendingRegistration(
            ID=str(uuid4()),
            USER_ID=123,
        ),
        PendingRegistration(
            ID=str(uuid4()),
            USER_ID=1,
            NEW_EMAIL="janesmith@h4i.com",
        ),
        PendingRegistration(
            ID="167283681723781726381763181920914351",
            USER_ID=1,
            NEW_EMAIL="janesmith@h4i.com",
        ),
        PendingRegistration(
            ID=str(uuid4()),
            USER_ID=1,
            NEW_EMAIL="janesmith@h4i.com",
        ),
        PendingRegistration(
            ID=str(uuid4()),
            USER_ID=2,
        ),
    ]
    for registration in registrations:
        db_session.add(registration)
        db_session.commit()
    return registrations


@pytest.fixture
def get_account_serv(
    logger: Logger,
    test_user_repo: UsersRepository,
    test_pending_repo: PendingRegistrationRepository,
):
    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = True
    mock_ver.verify_verification_code_email.return_value = True
    return AccountService(logger, test_pending_repo, test_user_repo, mock_ver)


@pytest.fixture
def get_account_serv_no_email(
    logger: Logger,
    test_user_repo: UsersRepository,
    test_pending_repo: PendingRegistrationRepository,
):
    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = True
    mock_ver.verify_verification_code_email.return_value = True
    return AccountService(logger, test_pending_repo, test_user_repo, mock_ver)


@pytest.fixture
def app():
    from src.main import app

    return app


@pytest.fixture
def client(app: FastAPI):
    return TestClient(app)


def test_controller_activates_account(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    status_code = 200
    body_keys = ["qr_token", "uuid", "type"]
    body_values: list[Any] = ["123465", "2", ActivationType.NEW_ACCOUNT.value]

    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/activate",
        json={
            "id": test_pending_registrations[5].ID,
            "verification_code": "123456",
            "verification_type": "sms",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == status_code
    result = response.json()
    keys = result.keys()
    vals = result.values()
    for key in body_keys:
        assert key in keys
    for val in body_values:
        assert val in vals


def test_controller_updates_email(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    status_code = 200
    body_keys = ["qr_token", "uuid", "type"]
    body_values: list[Any] = ["123", "1", ActivationType.UPDATE_EMAIL.value]

    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/activate",
        json={
            "id": test_pending_registrations[2].ID,
            "verification_code": "123456",
            "verification_type": "email",
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == status_code
    result = response.json()
    keys = result.keys()
    vals = result.values()
    for key in body_keys:
        assert key in keys
    for val in body_values:
        assert val in vals


def test_controller_rejects_invalid_uuid(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    status_code = 400
    body_keys = ["detail"]
    body_values: list[Any] = ["invalid id: ID must be valid uuid"]

    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/activate",
        json={
            "id": test_pending_registrations[3].ID,
            "verification_code": "123456",
            "verification_type": "sms",
        },
    )
    app.dependency_overrides.clear()
    assert response.status_code == status_code
    result = response.json()
    keys = result.keys()
    vals = result.values()
    for key in body_keys:
        assert key in keys
    for val in body_values:
        assert val in vals


def test_controller_rejects_invalid_verification_code(
    client: TestClient,
    app: FastAPI,
    logger: Logger,
    test_pending_repo: PendingRegistrationRepository,
    test_user_repo: UsersRepository,
    test_users: list[User],
    test_pending_registrations: list[PendingRegistration],
):
    status_code = 400
    body_keys = ["detail"]
    body_values: list[str] = [
        "invalid verification code: Verification code must be exactly 6 digits"
    ]

    mock_ver = Mock()
    mock_ver.verify_verification_code.return_value = False
    mock_ver.verify_verification_code_email.return_value = False
    account_serv = AccountService(logger, test_pending_repo, test_user_repo, mock_ver)

    app.dependency_overrides[get_account_service] = lambda: account_serv

    response = client.post(
        "/accounts/activate",
        json={
            "id": test_pending_registrations[4].ID,
            "verification_code": "1234",
            "verification_type": "sms",
        },
    )
    app.dependency_overrides.clear()
    assert response.status_code == status_code
    result = response.json()
    keys = result.keys()
    vals = result.values()
    for key in body_keys:
        assert key in keys
    for val in body_values:
        assert val in vals


def test_controller_gets_user_profiles(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_race_lookup: list[tuple[int, str]],
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    dob_str = (
        test_users[0].date_of_birth.strftime("%Y-%m-%d")
        if test_users[0].date_of_birth is not None
        else ""
    )

    mock_dict: defaultdict[str, str | None] = defaultdict(str)
    mock_dict["first_name"] = test_users[0].first_name
    mock_dict["last_name"] = test_users[0].last_name
    mock_dict["email"] = test_users[0].email
    mock_dict["phone_number"] = test_users[0].phone_number
    mock_dict["date_of_birth"] = dob_str
    mock_dict["zip_code"] = test_users[0].zip_code
    mock_dict["address"] = test_users[0].address
    mock_dict["race"] = get_account_serv.usersRepository.get_race(
        test_users[0].id, test_users[0].race_id
    )

    response = client.get("/accounts/userProfile/1")

    assert response.status_code == 200
    assert response.json() == mock_dict


def test_controller_update_profile_non_email_fields(
    client: TestClient,
    app: FastAPI,
    get_account_serv_no_email: AccountService,
    test_users: list[User],
    test_race_lookup: list[tuple[int, str]],
):
    from unittest.mock import patch

    from src.Utils.Validators import Validator

    app.dependency_overrides[get_account_service] = lambda: get_account_serv_no_email

    with patch.object(Validator, "validate_uuid_string", return_value="1"):
        response = client.put(
            "/accounts/userProfile/1",
            json={"first_name": "Janet", "zip_code": "99999"},
        )

    app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert result["message"] == "Profile updated successfully."
    assert result["first_name"] == "Janet"
    assert result["zip_code"] == "99999"
    assert result["pending_registration_id"] is None


def test_controller_update_profile_invalid_uuid_returns_400(
    client: TestClient,
    app: FastAPI,
    get_account_serv_no_email: AccountService,
    test_users: list[User],
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv_no_email

    response = client.put(
        "/accounts/userProfile/not-a-valid-uuid",
        json={"first_name": "Janet"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 400
    assert "Invalid token" in response.json()["detail"]


def test_controller_update_profile_unknown_user_returns_404(
    client: TestClient,
    app: FastAPI,
    get_account_serv_no_email: AccountService,
    test_users: list[User],
):
    import uuid

    app.dependency_overrides[get_account_service] = lambda: get_account_serv_no_email

    response = client.put(
        f"/accounts/userProfile/{uuid.uuid4()}",
        json={"first_name": "Ghost"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_controller_update_profile_rejects_both_email_and_phone(
    client: TestClient,
    app: FastAPI,
    get_account_serv_no_email: AccountService,
    test_users: list[User],
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv_no_email

    response = client.put(
        "/accounts/userProfile/1",
        json={"email": "newemail@example.com", "phone_number": "123-456-7890"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 422


@pytest.fixture
def test_parent_user(db_session: Session):
    parent = User(
        id="550e8400-e29b-41d4-a716-446655440000",
        first_name="Jane",
        last_name="Smith",
        email="jane@gmail.com",
        phone_number=None,
        date_of_birth=date(2000, 12, 12),
        zip_code="12345",
        address="3675 Market St",
        race_id=1,
        qr_token="parent-qr-token",
        is_active=True,
        parent_id=None,
    )
    db_session.add(parent)
    db_session.commit()
    return parent


def test_controller_add_child(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_parent_user: User,
    test_race_lookup: list[tuple[int, str]],
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/add-child",
        json={
            "parent_id": test_parent_user.id,
            "first_name": "Kid",
            "last_name": "Smith",
            "date_of_birth": "2015-06-01",
            "zip_code": "12345",
            "address": "3675 Market St",
            "race_id": 1,
        },
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    result = response.json()
    assert result["first_name"] == "Kid"
    assert result["email"] == test_parent_user.email
    assert result["parent_id"] == test_parent_user.id
    assert result["qr_token"] is not None


def test_controller_lookup_users_by_email(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_race_lookup: list[tuple[int, str]],
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/lookup",
        json={"email": "jane@gmail.com"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    result: list[dict[str, object]] = cast(list[dict[str, object]], response.json())
    assert isinstance(result, list)
    assert len(result) == 1


def test_controller_lookup_users_by_phone(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_race_lookup: list[tuple[int, str]],
):
    test_users[0].email = None
    test_users[0].phone_number = "1234567890"
    test_users[0].is_active = True
    get_account_serv.usersRepository.db.commit()

    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/lookup",
        json={"phone_number": "1234567890"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    result: list[dict[str, object]] = cast(list[dict[str, object]], response.json())
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["first_name"] == "Jane"


def test_controller_lookup_users_rejects_both(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/lookup",
        json={"email": "jane@gmail.com", "phone_number": "123-456-7890"},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_controller_lookup_users_rejects_neither(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/lookup",
        json={},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 422


def test_controller_lookup_users_normalizes_email(
    client: TestClient,
    app: FastAPI,
    get_account_serv: AccountService,
    test_users: list[User],
    test_race_lookup: list[tuple[int, str]],
):
    app.dependency_overrides[get_account_service] = lambda: get_account_serv

    response = client.post(
        "/accounts/lookup",
        json={"email": " JANE@gmail.com "},
    )
    app.dependency_overrides.clear()

    assert response.status_code == 200
    result: list[dict[str, object]] = cast(list[dict[str, object]], response.json())
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["first_name"] == "Jane"


def _make_paginated_record(
    first_name: str | None = "Helen",
    last_name: str | None = "Troy",
    parent_first_name: str | None = None,
    parent_last_name: str | None = None,
) -> DisplayUserRecord:
    return DisplayUserRecord(
        first_name=first_name,
        last_name=last_name,
        email="helen@example.com",
        phone_number="5559990000",
        date_of_birth="1970-11-05",
        zip_code="19103",
        address="3 Pine St",
        race_description="White",
        is_active=True,
        parent_first_name=parent_first_name,
        parent_last_name=parent_last_name,
    )


def test_controller_get_users_paginated_returns_200(
    client: TestClient,
    app: FastAPI,
):
    from unittest.mock import MagicMock

    mock_service = MagicMock()
    mock_service.get_users_paginated.return_value = [_make_paginated_record()]
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = client.get("/accounts/users/paginated?page=1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_controller_get_users_paginated_response_has_expected_fields(
    client: TestClient,
    app: FastAPI,
):
    from unittest.mock import MagicMock

    mock_service = MagicMock()
    mock_service.get_users_paginated.return_value = [_make_paginated_record()]
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = client.get("/accounts/users/paginated?page=1")

    app.dependency_overrides.clear()

    expected_keys = {
        "first_name",
        "last_name",
        "email",
        "phone_number",
        "date_of_birth",
        "zip_code",
        "address",
        "race_description",
        "is_active",
        "parent_first_name",
        "parent_last_name",
    }
    assert expected_keys == response.json()[0].keys()


def test_controller_get_users_paginated_top_level_has_null_parent_fields(
    client: TestClient,
    app: FastAPI,
):
    from unittest.mock import MagicMock

    mock_service = MagicMock()
    mock_service.get_users_paginated.return_value = [_make_paginated_record()]
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = client.get("/accounts/users/paginated?page=1")

    app.dependency_overrides.clear()

    result = response.json()[0]
    assert result["parent_first_name"] is None
    assert result["parent_last_name"] is None


def test_controller_get_users_paginated_child_has_resolved_parent_names(
    client: TestClient,
    app: FastAPI,
):
    from unittest.mock import MagicMock

    mock_service = MagicMock()
    mock_service.get_users_paginated.return_value = [
        _make_paginated_record(
            first_name="Paris", parent_first_name="Helen", parent_last_name="Troy"
        ),  # noqa: E501
    ]
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = client.get("/accounts/users/paginated?page=1")

    app.dependency_overrides.clear()

    result = response.json()[0]
    assert result["parent_first_name"] == "Helen"
    assert result["parent_last_name"] == "Troy"


def test_controller_get_users_paginated_empty_returns_empty_list(
    client: TestClient,
    app: FastAPI,
):
    from unittest.mock import MagicMock

    mock_service = MagicMock()
    mock_service.get_users_paginated.return_value = []
    app.dependency_overrides[get_account_service] = lambda: mock_service

    response = client.get("/accounts/users/paginated?page=1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == []
