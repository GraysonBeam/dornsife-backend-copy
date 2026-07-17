import os
from logging import Logger, getLogger
from unittest.mock import MagicMock

os.environ["VERIFICATION_TTL"] = "1440"

from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Controllers.UserRegisterController import get_user_reg_service
from src.Models.User import Base, RaceLookup
from src.Repositories.PendingRegistrationRepository import PendingRegistrationRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Schemas.UserRegistrationRequest import UserRegistrationRequest
from src.Services.UserRegisterService import UserRegisterService
from src.Services.VerificationService import VerificationStatus


@pytest.fixture
def app():
    from src.main import app

    return app


@pytest.fixture
def client(app: FastAPI):
    return TestClient(app)


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        # removes the checker because the test client intance is running on a diff thread
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def logger():
    return getLogger()


@pytest.fixture
def get_user_repo(logger: Logger, db_session: Session):
    return UsersRepository(logger, db_session)


@pytest.fixture
def get_user_reg_serv(logger: Logger, db_session: Session, get_user_repo: UsersRepository):
    pending_reg_repo = PendingRegistrationRepository(logger, db_session)
    mock_ver = Mock()
    mock_ver.send_sms_verification_code.return_value = VerificationStatus.APPROVED
    mock_ver.send_email_verification_code.return_value = VerificationStatus.APPROVED
    return UserRegisterService(logger, get_user_repo, pending_reg_repo, mock_ver)


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
    for _id, race in mock_race_table.items():
        race = RaceLookup(race_id=_id, description=race)
        db_session.add(race)
        db_session.commit()
        race_lst.append((race.race_id, race.description))

    return race_lst


@pytest.fixture
def mock_user_payload() -> UserRegistrationRequest:
    return UserRegistrationRequest(
        first_name="John",
        last_name="Doe",
        email="john.doe@example.com",
        date_of_birth="1990-01-01",
        zip_code="62704",
        address="123 Main St",
        race_id=1,
    )


def test_controller_returns_all_race_options(
    client: TestClient,
    app: FastAPI,
    get_user_reg_serv: UserRegisterService,
    test_race_lookup: list[tuple[int, str]],
):
    # this is just to clear up the params when running for local db session
    app.dependency_overrides[get_user_reg_service] = lambda: get_user_reg_serv

    response = client.get("/userRegistration/raceOptions")
    app.dependency_overrides.clear()

    assert response.status_code == 200
    data = response.json()
    expected = [{"key": description, "id": race_id} for race_id, description in test_race_lookup]
    assert data["races"] == expected, "get race options should return key + id objects"


def test_register_user_workflow_success(
    client: TestClient,
    app: FastAPI,
    get_user_reg_serv: UserRegisterService,
    mock_user_payload: UserRegistrationRequest,
):
    # Mock the return value of the service method
    expected_pending_id = "999"
    get_user_reg_serv.create_inactive_user = MagicMock(return_value=expected_pending_id)

    app.dependency_overrides[get_user_reg_service] = lambda: get_user_reg_serv

    response = client.post("/userRegistration/user", json=mock_user_payload.model_dump())

    assert response.status_code == 200
    assert response.json()["pending_registration_id"] == expected_pending_id
    app.dependency_overrides.clear()


def test_register_user_workflow_failure(
    client: TestClient,
    app: FastAPI,
    get_user_reg_serv: UserRegisterService,
    mock_user_payload: UserRegistrationRequest,
):
    """
    Test that the controller returns a 500 error if the service logic fails.
    """
    get_user_reg_serv.create_inactive_user = MagicMock(return_value=None)

    app.dependency_overrides[get_user_reg_service] = lambda: get_user_reg_serv

    response = client.post("/userRegistration/user", json=mock_user_payload.model_dump())

    assert response.status_code == 500
    assert response.json()["detail"] == "Registration failed"

    app.dependency_overrides.clear()


def test_register_user_rejects_both_email_and_phone(
    client: TestClient,
    app: FastAPI,
    get_user_reg_serv: UserRegisterService,
    mock_user_payload: UserRegistrationRequest,
):
    app.dependency_overrides[get_user_reg_service] = lambda: get_user_reg_serv

    response = client.post(
        "/userRegistration/user",
        json={**mock_user_payload.model_dump(), "phone_number": "1234567890"},
    )

    assert response.status_code == 422
    app.dependency_overrides.clear()
