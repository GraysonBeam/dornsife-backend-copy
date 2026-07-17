from collections.abc import Generator
from datetime import UTC, date, datetime
from logging import Logger, getLogger

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.Attendance import Attendance
from src.Models.Base import Base
from src.Models.CheckInMethodType import CheckInMethodsEnum, CheckInMethodType
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Models.User import RaceLookup, User
from src.Repositories.AttendanceRepository import AttendanceRepository
from src.Services.AdminAnalyticsService import AdminAnalyticsService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create an in-memory SQLite database for testing."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # Create all tables at once using Base metadata
    Base.metadata.create_all(engine)

    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Add test data
    race = RaceLookup(race_id=1, description="Asian")
    session.add(race)

    event_type = EventType(id=1, type="Workshop")
    session.add(event_type)

    check_in_method = CheckInMethodType(
        checkinid=CheckInMethodsEnum.QR_CODE.value, methodtype="QR code"
    )
    session.add(check_in_method)

    # Create test users with date_of_birth
    user1 = User(
        id="user1",
        first_name="John",
        last_name="Doe",
        email="john@example.com",
        date_of_birth=date(2000, 1, 15),
        zip_code="60603",
        race_id=1,
        parent_id=None,
    )
    user2 = User(
        id="user2",
        first_name="Jane",
        last_name="Smith",
        email="jane@example.com",
        date_of_birth=date(2010, 5, 20),
        zip_code="60610",
        race_id=1,
        parent_id="parent1",
    )
    session.add(user1)
    session.add(user2)

    # Create test events with timezone-aware datetimes
    event1 = Event(
        id="event1",
        name="Community Workshop",
        start_datetime=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        end_datetime=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        location="Community Center",
        type_id=1,
    )
    event2 = Event(
        id="event2",
        name="Training Session",
        start_datetime=datetime(2024, 1, 20, 14, 0, 0, tzinfo=UTC),
        end_datetime=datetime(2024, 1, 20, 16, 0, 0, tzinfo=UTC),
        location="Training Hall",
        type_id=1,
    )
    session.add(event1)
    session.add(event2)

    session.commit()

    # Create attendance records
    attendance1 = Attendance(
        id="att1",
        user_id="user1",
        event_instance_id="event1",
        check_in_method_id=CheckInMethodsEnum.QR_CODE.value,
        check_in_time=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
    )
    attendance2 = Attendance(
        id="att2",
        user_id="user2",
        event_instance_id="event1",
        check_in_method_id=CheckInMethodsEnum.QR_CODE.value,
        check_in_time=datetime(2024, 1, 15, 10, 45, 0, tzinfo=UTC),
    )
    attendance3 = Attendance(
        id="att3",
        user_id="user1",
        event_instance_id="event2",
        check_in_method_id=CheckInMethodsEnum.QR_CODE.value,
        check_in_time=datetime(2024, 1, 20, 14, 15, 0, tzinfo=UTC),
    )
    session.add(attendance1)
    session.add(attendance2)
    session.add(attendance3)
    session.commit()

    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def logger() -> Logger:
    return getLogger("test_logger")


@pytest.fixture
def attendance_repository(logger: Logger, db_session: Session) -> AttendanceRepository:
    return AttendanceRepository(logger, db_session)


@pytest.fixture
def admin_analytics_service(
    logger: Logger, attendance_repository: AttendanceRepository
) -> AdminAnalyticsService:
    return AdminAnalyticsService(logger, attendance_repository)


class TestAdminAnalyticsService:
    """Tests for AdminAnalyticsService."""

    def test_get_attendance_data_after_date_returns_records_after_date(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test get_attendance_data_after_date returns only records after the specified date."""
        # Use a date after event1 but before or equal to event2
        query_date = datetime(2024, 1, 16, 0, 0, 0, tzinfo=UTC)
        result = admin_analytics_service.get_attendance_data_after_date(query_date)

        assert result.total_count == 1
        assert len(result.records) == 1
        assert result.records[0].event_name == "Training Session"

    def test_get_attendance_data_after_date_returns_all_records_before_earliest_event(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test get_attendance_data_after_date returns all records when date before all events."""
        query_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = admin_analytics_service.get_attendance_data_after_date(query_date)

        assert result.total_count == 3
        assert len(result.records) == 3

    def test_get_attendance_data_after_date_returns_empty_when_no_records_after_date(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test get_attendance_data_after_date returns empty list when no records after date."""
        query_date = datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = admin_analytics_service.get_attendance_data_after_date(query_date)

        assert result.total_count == 0
        assert len(result.records) == 0

    def test_get_attendance_data_after_date_includes_user_info(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test that returned records include correct user information."""
        query_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = admin_analytics_service.get_attendance_data_after_date(query_date)

        # Find the record for user1
        user1_records = [r for r in result.records if r.event_name == "Community Workshop"]
        assert len(user1_records) > 0

        record = user1_records[0]
        assert record.user_zip_code == "60603"
        assert record.has_parent is False
        assert record.user_race == "Asian"

    def test_get_attendance_data_after_date_includes_parent_info(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test that returned records correctly identify users with parents."""
        query_date = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        result = admin_analytics_service.get_attendance_data_after_date(query_date)

        # Find the record for user2 (who has a parent)
        user2_records = [r for r in result.records if r.user_zip_code == "60610"]
        assert len(user2_records) > 0

        record = user2_records[0]
        assert record.has_parent is True

    def test_get_attendance_data_by_event_id_returns_correct_event_data(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test that get_attendance_data_by_event_id returns only records for specified event."""
        result = admin_analytics_service.get_attendance_data_by_event_id("event1")

        assert result.total_count == 2
        assert len(result.records) == 2

        # All records should be for event1
        for record in result.records:
            assert record.event_name == "Community Workshop"

    def test_get_attendance_data_by_event_id_with_no_records(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test get_attendance_data_by_event_id returns empty list for event with no records."""
        # Create an event with no attendance
        result = admin_analytics_service.get_attendance_data_by_event_id("nonexistent_event")

        assert result.total_count == 0
        assert len(result.records) == 0

    def test_get_attendance_data_by_event_id_includes_event_details(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test that returned records include all event details."""
        result = admin_analytics_service.get_attendance_data_by_event_id("event2")

        assert result.total_count == 1
        record = result.records[0]

        assert record.event_name == "Training Session"
        assert record.event_location == "Training Hall"
        assert record.event_type == "Workshop"
        # SQLite may strip timezone info, so compare without timezone
        assert record.event_start_time.replace(tzinfo=None) == datetime(2024, 1, 20, 14, 0, 0)
        assert record.event_end_time.replace(tzinfo=None) == datetime(2024, 1, 20, 16, 0, 0)

    def test_get_attendance_data_by_event_id_includes_check_in_method(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test that returned records include check-in method."""
        result = admin_analytics_service.get_attendance_data_by_event_id("event1")

        for record in result.records:
            assert record.check_in_method == "QR code"

    def test_response_objects_have_correct_type(
        self, admin_analytics_service: AdminAnalyticsService
    ):
        """Test that service returns correct response object types."""
        from src.Schemas.DataAfterDateResponse import DataAfterDateResponse
        from src.Schemas.EventAttendanceDataResponse import EventAttendanceDataResponse

        result1 = admin_analytics_service.get_attendance_data_after_date(
            datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        )
        assert isinstance(result1, DataAfterDateResponse)

        result2 = admin_analytics_service.get_attendance_data_by_event_id("event1")
        assert isinstance(result2, EventAttendanceDataResponse)
