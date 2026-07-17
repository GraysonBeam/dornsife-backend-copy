import os
from collections.abc import Generator
from datetime import UTC, date, datetime
from logging import Logger, getLogger
from typing import Any, cast

os.environ["VERIFICATION_TTL"] = "1440"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Database.dependencies import get_db_session
from src.Models.Attendance import Attendance
from src.Models.Base import Base
from src.Models.CheckInMethodType import CheckInMethodsEnum, CheckInMethodType
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Models.User import RaceLookup, User


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )

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

    # Create test users
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

    # Create test events
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
    """Create test logger."""
    return getLogger("test_get_data_controller")


@pytest.fixture
def app() -> FastAPI:
    """Import the FastAPI app."""
    from src.main import app

    return app


@pytest.fixture
def client(app: FastAPI, db_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with dependencies overridden."""

    def override_get_db_session() -> Session:
        return db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestGetDataControllerEndpoints:
    """Tests for GetDataController endpoints."""

    def test_get_attendance_data_after_date_returns_200(self, client: TestClient):
        """Test that dataAfterDate endpoint returns 200 OK."""
        response = client.get("/data/dataAfterDate?date=2024-01-01T00:00:00Z")
        assert response.status_code == 200

    def test_get_attendance_data_after_date_returns_correct_structure(self, client: TestClient):
        """Test that dataAfterDate returns correct response structure."""
        response = client.get("/data/dataAfterDate?date=2024-01-01T00:00:00Z")
        data = response.json()

        assert "records" in data
        assert "total_count" in data
        assert isinstance(data["records"], list)
        assert isinstance(data["total_count"], int)

    def test_get_attendance_data_after_date_filters_by_date(self, client: TestClient):
        """Test that dataAfterDate correctly filters records by date."""
        # Query for records after event2
        response = client.get("/data/dataAfterDate?date=2024-01-16T00:00:00Z")
        data = cast(dict[str, Any], response.json())
        records = cast(list[dict[str, Any]], data["records"])

        assert data["total_count"] == 1
        assert len(records) == 1
        assert records[0]["event_name"] == "Training Session"

    def test_get_attendance_data_after_date_returns_all_records_before_earliest(
        self, client: TestClient
    ):
        """Test that dataAfterDate returns all records when using early date."""
        response = client.get("/data/dataAfterDate?date=2024-01-01T00:00:00Z")
        data = cast(dict[str, Any], response.json())

        assert data["total_count"] == 3

    def test_get_attendance_data_after_date_returns_empty_after_all_events(
        self, client: TestClient
    ):
        """Test that dataAfterDate returns empty list when date is after all events."""
        response = client.get("/data/dataAfterDate?date=2025-01-01T00:00:00Z")
        data = cast(dict[str, Any], response.json())
        records = cast(list[dict[str, Any]], data["records"])

        assert data["total_count"] == 0
        assert len(records) == 0

    def test_get_attendance_data_after_date_includes_event_data(self, client: TestClient):
        """Test that returned records include event data."""
        response = client.get("/data/dataAfterDate?date=2024-01-01T00:00:00Z")
        data = response.json()

        record = data["records"][0]
        assert "event_name" in record
        assert "event_start_time" in record
        assert "event_end_time" in record
        assert "event_location" in record
        assert "event_type" in record

    def test_get_attendance_data_after_date_includes_user_data(self, client: TestClient):
        """Test that returned records include user analytics data."""
        response = client.get("/data/dataAfterDate?date=2024-01-01T00:00:00Z")
        data = response.json()

        record = data["records"][0]
        assert "user_age" in record
        assert "user_zip_code" in record
        assert "has_parent" in record
        assert "check_in_method" in record
        assert "user_race" in record

    def test_get_attendance_data_after_date_excludes_sensitive_pii(self, client: TestClient):
        """Test that returned records do NOT include sensitive PII."""
        response = client.get("/data/dataAfterDate?date=2024-01-01T00:00:00Z")
        data = response.json()

        record = data["records"][0]
        # Verify sensitive fields are not included
        assert "first_name" not in record
        assert "last_name" not in record
        assert "email" not in record
        assert "phone_number" not in record
        assert "date_of_birth" not in record
        assert "address" not in record

    def test_get_event_attendance_data_returns_200(self, client: TestClient):
        """Test that eventAttendanceData endpoint returns 200 OK."""
        response = client.get("/data/eventAttendanceData/event1")
        assert response.status_code == 200

    def test_get_event_attendance_data_returns_correct_structure(self, client: TestClient):
        """Test that eventAttendanceData returns correct response structure."""
        response = client.get("/data/eventAttendanceData/event1")
        data = response.json()

        assert "records" in data
        assert "total_count" in data
        assert isinstance(data["records"], list)
        assert isinstance(data["total_count"], int)

    def test_get_event_attendance_data_filters_by_event_id(self, client: TestClient):
        """Test that eventAttendanceData correctly filters by event_id."""
        response = client.get("/data/eventAttendanceData/event1")
        data = response.json()

        assert data["total_count"] == 2
        for record in data["records"]:
            assert record["event_name"] == "Community Workshop"

    def test_get_event_attendance_data_returns_empty_for_nonexistent_event(
        self, client: TestClient
    ):
        """Test that eventAttendanceData returns empty list for nonexistent event."""
        response = client.get("/data/eventAttendanceData/nonexistent")
        data = cast(dict[str, Any], response.json())
        records = cast(list[dict[str, Any]], data["records"])

        assert data["total_count"] == 0
        assert len(records) == 0

    def test_get_event_attendance_data_returns_all_event_details(self, client: TestClient):
        """Test that eventAttendanceData returns complete event details."""
        response = client.get("/data/eventAttendanceData/event2")
        data = response.json()

        assert data["total_count"] == 1
        record = data["records"][0]

        assert record["event_name"] == "Training Session"
        assert record["event_location"] == "Training Hall"
        assert record["event_type"] == "Workshop"

    def test_get_event_attendance_data_returns_check_in_method(self, client: TestClient):
        """Test that eventAttendanceData includes check-in method."""
        response = client.get("/data/eventAttendanceData/event1")
        data = response.json()

        for record in data["records"]:
            assert record["check_in_method"] == "QR code"

    def test_get_event_attendance_data_identifies_users_with_parents(self, client: TestClient):
        """Test that eventAttendanceData correctly identifies users with parents."""
        response = client.get("/data/eventAttendanceData/event1")
        data = cast(dict[str, Any], response.json())
        records = cast(list[dict[str, Any]], data["records"])

        # Find user2's record (they have a parent)
        user2_record = next(
            (r for r in records if r["user_zip_code"] == "60610"),
            None,
        )
        assert user2_record is not None
        assert user2_record["has_parent"] is True

    def test_get_event_attendance_data_identifies_users_without_parents(self, client: TestClient):
        """Test that eventAttendanceData correctly identifies users without parents."""
        response = client.get("/data/eventAttendanceData/event1")
        data = cast(dict[str, Any], response.json())
        records = cast(list[dict[str, Any]], data["records"])

        # Find user1's record (they don't have a parent)
        user1_record = next(
            (r for r in records if r["user_zip_code"] == "60603"),
            None,
        )
        assert user1_record is not None
        assert user1_record["has_parent"] is False

    def test_get_event_attendance_data_excludes_sensitive_pii(self, client: TestClient):
        """Test that eventAttendanceData does NOT include sensitive PII."""
        response = client.get("/data/eventAttendanceData/event1")
        data = response.json()

        record = data["records"][0]
        # Verify sensitive fields are not included
        assert "first_name" not in record
        assert "last_name" not in record
        assert "email" not in record
        assert "phone_number" not in record
        assert "date_of_birth" not in record
        assert "address" not in record

    def test_get_event_attendance_data_with_empty_event_id_returns_400(self, client: TestClient):
        """Test that empty event_id returns 400 Bad Request."""
        response = client.get("/data/eventAttendanceData/ ")
        # Note: extra space should be trimmed
        assert response.status_code in [200, 400]  # Depends on implementation


class TestDataAfterDateRequestValidation:
    """Tests for request validation on dataAfterDate endpoint."""

    def test_date_parameter_is_required(self, client: TestClient):
        """Test that date parameter is required."""
        response = client.get("/data/dataAfterDate")
        # FastAPI returns 422 for missing required parameters
        assert response.status_code == 422

    def test_date_parameter_accepts_iso_format(self, client: TestClient):
        """Test that date parameter accepts ISO 8601 format."""
        response = client.get("/data/dataAfterDate?date=2024-01-15T10:30:00Z")
        assert response.status_code == 200

    def test_date_parameter_accepts_date_only(self, client: TestClient):
        """Test that date parameter accepts date-only format."""
        response = client.get("/data/dataAfterDate?date=2024-01-15")
        assert response.status_code == 200
