from datetime import datetime
from logging import Logger, getLogger
from typing import cast

import pytest
from sqlalchemy import Table, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.Attendance import Attendance
from src.Models.CheckInMethodType import CheckInMethodsEnum, CheckInMethodType
from src.Models.CheckInProof import CheckInProof
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Models.exceptions import NotFoundException
from src.Models.User import RaceLookup, User
from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Repositories.UsersRepository import UsersRepository
from src.Services.AttendanceService import AttendanceService
from src.Utils.Validators import ValidationError, Validator


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    cast(Table, RaceLookup.__table__).create(engine, checkfirst=True)
    cast(Table, User.__table__).create(engine, checkfirst=True)
    cast(Table, EventType.__table__).create(engine, checkfirst=True)
    cast(Table, Event.__table__).create(engine, checkfirst=True)
    cast(Table, CheckInMethodType.__table__).create(engine, checkfirst=True)
    cast(Table, Attendance.__table__).create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    session = Session()

    race = RaceLookup(race_id=1, description="Test Race")
    session.add(race)

    event_type = EventType(id=1, type="Test Event Type")
    session.add(event_type)

    check_in_method = CheckInMethodType(checkinid=1, methodtype="QR code")
    session.add(check_in_method)

    session.commit()
    yield session
    session.close()


@pytest.fixture
def logger() -> Logger:
    return getLogger("test_logger")


@pytest.fixture
def test_attendance_service(
    logger: Logger,
    db_session: Session,
) -> AttendanceService:
    attendanceRepo = AttendanceRepository(logger, db_session)
    usersRepo = UsersRepository(logger, db_session)
    return AttendanceService(logger, attendanceRepo, usersRepo)


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


def test_check_into_event_throws_error_if_user_from_qr_token_does_not_exist(
    test_attendance_service: AttendanceService,
) -> None:
    with pytest.raises(NotFoundException) as e:
        test_attendance_service.check_into_event(
            "test_token", "1", CheckInMethodsEnum.QR_CODE.value
        )

    assert "User not found from qr_token provided" in str(e)


def test_check_into_event_throws_error_if_attendance_record_already_exists(
    test_attendance_service: AttendanceService,
    test_user: User,
    test_event: Event,
    test_attendance: Attendance,
) -> None:
    assert test_user is not None
    assert test_user.qr_token is not None
    with pytest.raises(ValidationError) as e:
        test_attendance_service.check_into_event(
            test_user.qr_token, test_event.id, CheckInMethodsEnum.QR_CODE.value
        )

    assert "already exists" in str(e).lower()


def test_check_into_event_success(
    test_attendance_service: AttendanceService,
    test_user: User,
    test_event: Event,
) -> None:
    assert test_event is not None
    assert test_user.qr_token is not None

    result: CheckInProof = test_attendance_service.check_into_event(
        test_user.qr_token, test_event.id, CheckInMethodsEnum.QR_CODE.value
    )

    assert result is not None
    assert Validator.validate_uuid_string(result.attendance_id)


def test_get_event_attendance_returns_records(
    test_attendance_service: AttendanceService,
    test_attendance: Attendance,
    test_event: Event,
) -> None:
    records = test_attendance_service.get_event_attendance(test_event.id)

    assert len(records) == 1
    assert records[0].id == test_attendance.id
    assert records[0].user is not None
    assert records[0].user.first_name == "John"
    assert records[0].user.last_name == "Doe"


def test_get_event_attendance_returns_empty_list(
    test_attendance_service: AttendanceService,
    test_event: Event,
) -> None:
    records = test_attendance_service.get_event_attendance(test_event.id)

    assert records == []


def test_get_event_attendance_invalid_event(
    test_attendance_service: AttendanceService,
) -> None:
    records = test_attendance_service.get_event_attendance("nonexistent_event_id")

    assert records == []
