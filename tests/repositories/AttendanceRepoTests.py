from datetime import datetime
from logging import Logger, getLogger
from typing import cast

import pytest
from sqlalchemy import Table, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from src.Models.Attendance import Attendance
from src.Models.CheckInMethodType import CheckInMethodType
from src.Models.CheckInProof import CheckInProof
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Models.User import RaceLookup, User
from src.Repositories.AttendanceRepository import AttendanceRepository
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
def logger():
    return getLogger("test_logger")


@pytest.fixture
def attendance_repo(logger: Logger, db_session: Session):
    return AttendanceRepository(logger, db_session)


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


def test_delete_success(
    attendance_repo: AttendanceRepository, db_session: Session, test_attendance: Attendance
):
    attendance_id = test_attendance.id
    result = attendance_repo.delete_by_id(attendance_id)
    db_session.commit()

    assert result == "RECORD_DELETED"

    db_session.expire_all()
    deleted_record = db_session.get(Attendance, attendance_id)
    assert deleted_record is None


def test_delete_not_found(attendance_repo: AttendanceRepository):
    result = attendance_repo.delete_by_id("test")

    assert result == "NOT_FOUND"


def test_delete_integrity_error_propagation(
    attendance_repo: AttendanceRepository, db_session: Session, test_attendance: Attendance
):
    original_delete = db_session.delete

    def mock_delete(instance: object):
        raise IntegrityError("mock", params=None, orig=BaseException())

    db_session.delete = mock_delete

    with pytest.raises(IntegrityError):
        attendance_repo.delete_by_id(test_attendance.id)

    db_session.delete = original_delete


def test_create_attendance_record_success(
    attendance_repo: AttendanceRepository, db_session: Session, test_user: User, test_event: Event
):
    check_in_proof: CheckInProof = attendance_repo.create_attendance_record(
        test_user.id, test_event.id, 1
    )
    assert Validator.validate_uuid_string(check_in_proof.attendance_id)


def test_create_attendance_record_already_exists(
    attendance_repo: AttendanceRepository, db_session: Session, test_attendance: Attendance
):
    assert test_attendance.user_id is not None
    with pytest.raises(ValidationError) as e:
        attendance_repo.create_attendance_record(
            test_attendance.user_id,
            test_attendance.event_instance_id,
            test_attendance.check_in_method_id,
        )

    assert "already exists" in str(e).lower()


def test_get_attendance_by_event_id_returns_records(
    attendance_repo: AttendanceRepository, test_attendance: Attendance, test_event: Event
):
    records = attendance_repo.get_attendance_by_event_id(test_event.id)

    assert len(records) == 1
    assert records[0].id == test_attendance.id
    assert records[0].user is not None
    assert records[0].user.first_name == "John"
    assert records[0].user.last_name == "Doe"


def test_get_attendance_by_event_id_returns_empty_list(
    attendance_repo: AttendanceRepository, test_event: Event
):
    records = attendance_repo.get_attendance_by_event_id(test_event.id)

    assert records == []


def test_get_attendance_by_event_id_invalid_event(
    attendance_repo: AttendanceRepository,
):
    records = attendance_repo.get_attendance_by_event_id("nonexistent_event_id")

    assert records == []


def test_get_attendance_by_event_id_null_user(
    attendance_repo: AttendanceRepository, db_session: Session, test_event: Event
):
    attendance = Attendance(
        id="2",
        user_id=None,
        event_instance_id=test_event.id,
        check_in_method_id=1,
        check_in_time=datetime.now(),
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(attendance)
    db_session.commit()

    records = attendance_repo.get_attendance_by_event_id(test_event.id)

    assert len(records) == 1
    assert records[0].user is None
