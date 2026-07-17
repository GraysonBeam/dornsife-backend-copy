from datetime import datetime
from logging import Logger, getLogger
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Controllers.AttendanceController import get_attendance_service, get_event_reg_serv
from src.Models.Attendance import Attendance
from src.Models.CheckInMethodType import CheckInMethodType
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Models.User import RaceLookup, User
from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Repositories.EventsRepository import EventsRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Services.AttendanceService import AttendanceService
from src.Services.EventRegisterService import EventRegisterService

EVENT_ID = "3fa85f64-5717-4562-b3fc-2c963f66afa6"


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        # removes the checker because the test client intance is running on a diff thread
        connect_args={"check_same_thread": False},
    )
    cast(Table, RaceLookup.__table__).create(engine, checkfirst=True)
    cast(Table, User.__table__).create(engine, checkfirst=True)
    cast(Table, EventType.__table__).create(engine, checkfirst=True)
    cast(Table, Event.__table__).create(engine, checkfirst=True)
    cast(Table, CheckInMethodType.__table__).create(engine, checkfirst=True)
    cast(Table, Attendance.__table__).create(engine, checkfirst=True)
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    race = RaceLookup(race_id=1, description="Test Race")
    session.add(race)

    event_type = EventType(id=1, type="Test Event Type")
    session.add(event_type)

    check_in_method = CheckInMethodType(checkinid=1, methodtype="QR code")
    session.add(check_in_method)

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
def test_attendance_repo(logger: Logger, db_session: Session):
    return AttendanceRepository(logger, db_session)


@pytest.fixture
def test_events_repo(logger: Logger, db_session: Session):
    return EventsRepository(logger, db_session)


@pytest.fixture
def attendance_serv(
    logger: Logger, test_user_repo: UsersRepository, test_attendance_repo: AttendanceRepository
):
    return AttendanceService(logger, test_attendance_repo, test_user_repo)


@pytest.fixture
def event_reg_serv(
    logger: Logger,
    test_events_repo: EventsRepository,
):
    return EventRegisterService(logger, test_events_repo)


@pytest.fixture
def test_user(db_session: Session):
    user = User(
        id="1",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        phone_number="555-1234",
        date_of_birth=datetime(2000, 1, 1).date(),
        zip_code="12345",
        address="123 Main St",
        race_id=1,
        qr_token="test_token",
        is_active=True,
        parent_id=None,
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def test_event(db_session: Session):
    event = Event(
        id="1",
        name="Test Event",
        description="Test Description",
        start_datetime=datetime(2026, 2, 1, 10, 0),
        end_datetime=datetime(2026, 2, 1, 12, 0),
        location="Test Location",
        type_id=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(event)
    db_session.commit()
    return event


@pytest.fixture
def test_attendance(db_session: Session, test_user: User, test_event: Event):
    attendance = Attendance(
        id="1",
        user_id=test_user.id,
        event_instance_id=test_event.id,
        check_in_method_id=1,
        check_in_time=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(attendance)
    db_session.commit()
    return attendance


@pytest.fixture
def app():
    from src.main import app

    return app


@pytest.fixture
def client(app: FastAPI):
    return TestClient(app)


@pytest.fixture
def mock_dependencies(
    app: FastAPI,
    attendance_serv: AttendanceService,
    event_reg_serv: EventRegisterService,
):
    app.dependency_overrides[get_attendance_service] = lambda: attendance_serv
    app.dependency_overrides[get_event_reg_serv] = lambda: event_reg_serv

    yield app

    app.dependency_overrides.clear()


def test_attendance_controller_checks_in_for_event(
    client: TestClient,
    test_user: User,
    test_event: Event,
    mock_dependencies: FastAPI,
) -> None:
    response = client.post(
        "/attendance/checkIn",
        json={
            "qr_token": test_user.qr_token,
            "event_id": test_event.id,
            "is_manual_check_in": False,
        },
    )

    assert response.status_code == 200


def test_attendance_controller_denies_nonexistent_event_check_in(
    client: TestClient,
    mock_dependencies: FastAPI,
):
    response = client.post(
        "/attendance/checkIn",
        json={"qr_token": "test_token", "event_id": "1", "is_manual_check_in": False},
    )

    assert response.status_code == 404


def test_attendance_controller_denies_check_in_for_not_found_user(
    client: TestClient,
    mock_dependencies: FastAPI,
    test_event: Event,
):
    response = client.post(
        "/attendance/checkIn",
        json={"qr_token": "test_token", "event_id": test_event.id, "is_manual_check_in": False},
    )

    assert response.status_code == 404


def test_attendance_controller_denies_creating_duplicate_attendance_record(
    client: TestClient,
    mock_dependencies: FastAPI,
    test_user: User,
    test_event: Event,
    test_attendance: Attendance,
):
    response = client.post(
        "/attendance/checkIn",
        json={
            "qr_token": test_user.qr_token,
            "event_id": test_event.id,
            "is_manual_check_in": False,
        },
    )

    assert response.status_code == 400


def test_get_event_zip_bucket_returns_expected_shape(
    client: TestClient,
    app: FastAPI,
    attendance_serv: AttendanceService,
) -> None:
    attendance_serv.get_event_zip_bucket = MagicMock(
        return_value=[
            SimpleNamespace(zip_code="19104", zip_code_count=12),
            SimpleNamespace(zip_code="19103", zip_code_count=5),
        ]
    )
    app.dependency_overrides[get_attendance_service] = lambda: attendance_serv

    response = client.get("/attendance/event-zip-bucket", params={"event_id": EVENT_ID})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "buckets": [
            {"zip_code": "19104", "zip_code_count": 12},
            {"zip_code": "19103", "zip_code_count": 5},
        ]
    }
    attendance_serv.get_event_zip_bucket.assert_called_once_with(EVENT_ID)


def test_get_event_race_bucket_returns_expected_shape(
    client: TestClient,
    app: FastAPI,
    attendance_serv: AttendanceService,
) -> None:
    attendance_serv.get_event_race_bucket = MagicMock(
        return_value=[
            SimpleNamespace(description="White", race_count=8),
            SimpleNamespace(description="Other", race_count=2),
        ]
    )
    app.dependency_overrides[get_attendance_service] = lambda: attendance_serv

    response = client.get("/attendance/event-race-bucket", params={"event_id": EVENT_ID})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "buckets": [
            {"race": "White", "race_count": 8},
            {"race": "Other", "race_count": 2},
        ]
    }
    attendance_serv.get_event_race_bucket.assert_called_once_with(EVENT_ID)


def test_get_event_age_bucket_returns_expected_shape(
    client: TestClient,
    app: FastAPI,
    attendance_serv: AttendanceService,
) -> None:
    attendance_serv.get_event_age_bucket = MagicMock(
        return_value=[
            SimpleNamespace(age_bucket="18-24", attendee_count=4),
            SimpleNamespace(age_bucket="45+", attendee_count=10),
        ]
    )
    app.dependency_overrides[get_attendance_service] = lambda: attendance_serv

    response = client.get("/attendance/event-age-bucket", params={"event_id": EVENT_ID})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {
        "buckets": [
            {"age_bucket": "18-24", "attendee_count": 4},
            {"age_bucket": "45+", "attendee_count": 10},
        ]
    }
    attendance_serv.get_event_age_bucket.assert_called_once_with(EVENT_ID)


def test_get_event_zip_bucket_returns_empty_buckets(
    client: TestClient,
    app: FastAPI,
    attendance_serv: AttendanceService,
) -> None:
    attendance_serv.get_event_zip_bucket = MagicMock(return_value=[])
    app.dependency_overrides[get_attendance_service] = lambda: attendance_serv

    response = client.get("/attendance/event-zip-bucket", params={"event_id": EVENT_ID})

    app.dependency_overrides.clear()
    assert response.status_code == 200
    assert response.json() == {"buckets": []}


def test_get_event_zip_bucket_returns_500_on_service_error(
    client: TestClient,
    app: FastAPI,
    attendance_serv: AttendanceService,
) -> None:
    attendance_serv.get_event_zip_bucket = MagicMock(side_effect=RuntimeError("db down"))
    app.dependency_overrides[get_attendance_service] = lambda: attendance_serv

    response = client.get("/attendance/event-zip-bucket", params={"event_id": EVENT_ID})

    app.dependency_overrides.clear()
    assert response.status_code == 500
    assert response.json()["detail"] == "An Internal Server Error occurred."


def test_get_event_attendance_returns_attendees(
    client: TestClient,
    mock_dependencies: FastAPI,
    test_event: Event,
    test_attendance: Attendance,
    test_user: User,
):
    response = client.get(f"/attendance/event/{test_event.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == test_event.id
    attendees = body["attendees"]
    assert isinstance(attendees, list)
    assert attendees[0]["first_name"] == "John"
    assert attendees[0]["last_name"] == "Doe"


def test_get_event_attendance_returns_empty_list(
    client: TestClient,
    mock_dependencies: FastAPI,
    test_event: Event,
):
    response = client.get(f"/attendance/event/{test_event.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["event_id"] == test_event.id
    assert body["attendees"] == []


def test_get_event_attendance_nonexistent_event(
    client: TestClient,
    mock_dependencies: FastAPI,
):
    response = client.get("/attendance/event/nonexistent_event_id")

    assert response.status_code == 404
