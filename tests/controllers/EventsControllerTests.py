import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from logging import Logger, getLogger
from typing import Any, cast
from unittest.mock import Mock

os.environ["VERIFICATION_TTL"] = "1440"

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Controllers.EventsController import get_event_reg_serv
from src.Database.dependencies import get_db_session
from src.Models.Base import Base
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Repositories.EventsRepository import EventsRepository
from src.Services.EventRegisterService import EventRegisterService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Create in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocal = sessionmaker(bind=connection)
    session = SessionLocal()

    # Create test EventType
    event_type = EventType(type="Workshop")
    session.add(event_type)
    session.commit()

    yield session
    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture
def logger() -> Logger:
    """Create test logger."""
    return getLogger("test_events_controller")


@pytest.fixture
def test_event_type(db_session: Session) -> EventType | None:
    """Get the test event type from the database."""
    return db_session.query(EventType).filter(EventType.type == "Workshop").first()


@pytest.fixture
def events_repo(logger: Logger, db_session: Session) -> EventsRepository:
    """Create EventsRepository instance."""
    return EventsRepository(logger, db_session)


@pytest.fixture
def get_events_serv(logger: Logger, events_repo: EventsRepository) -> EventRegisterService:
    """Create EventRegisterService instance."""
    return EventRegisterService(logger, events_repo)


@pytest.fixture
def app() -> FastAPI:
    """Import the FastAPI app."""
    from src.main import app

    return app


@pytest.fixture
def client(app: FastAPI, db_session: Session) -> Generator[TestClient, None, None]:
    """Create test client with both dependencies overridden."""

    def override_get_db_session():
        return db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    yield TestClient(app)
    app.dependency_overrides.clear()


def make_event(
    db_session: Session,
    event_type_id: int,
    *,
    name: str = "Event",
    start_offset_hours: float = 6,
    end_offset_hours: float = 7,
) -> Event:
    """Helper to create an event in the database."""
    now = datetime.now(UTC)
    event = Event(
        name=name,
        description="",
        start_datetime=now + timedelta(hours=start_offset_hours),
        end_datetime=now + timedelta(hours=end_offset_hours),
        location="TBD",
        type_id=event_type_id,
    )
    db_session.add(event)
    db_session.commit()
    return event


# ============================================================================
# TEST: GET /events/activeEvents - Success Cases
# ============================================================================


def test_get_active_events_returns_200_with_empty_list(client: TestClient) -> None:
    """Test GET /events/activeEvents returns empty list when no events."""
    response = client.get("/events/activeEvents")

    assert response.status_code == 200
    assert response.json() == {"events": []}


def test_get_active_events_returns_200_with_events(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test GET /events/activeEvents returns events."""
    make_event(db_session, test_event_type.id, name="Soon")

    response = client.get("/events/activeEvents")

    assert response.status_code == 200
    response_data: dict[str, Any] = cast(dict[str, Any], response.json())
    events: list[Any] = cast(list[Any], response_data["events"])
    assert len(events) == 1


def test_get_active_events_response_shape(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test each event has required fields: id, name, start_datetime, end_datetime."""
    make_event(db_session, test_event_type.id, name="Soon")

    response = client.get("/events/activeEvents")

    assert response.status_code == 200
    response_data: dict[str, Any] = cast(dict[str, Any], response.json())
    events: list[Any] = cast(list[Any], response_data["events"])
    event_data: dict[str, Any] = cast(dict[str, Any], events[0])
    assert set(event_data.keys()) == {"id", "name", "start_datetime", "end_datetime"}


def test_get_active_events_response_values(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test event response contains correct values."""
    event = make_event(db_session, test_event_type.id, name="My Event")

    response = client.get("/events/activeEvents")

    assert response.status_code == 200
    response_data: dict[str, Any] = cast(dict[str, Any], response.json())
    events: list[Any] = cast(list[Any], response_data["events"])
    event_data: dict[str, Any] = cast(dict[str, Any], events[0])
    assert event_data["id"] == str(event.id)
    assert event_data["name"] == "My Event"


def test_get_active_events_returns_multiple(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test GET returns multiple events."""
    for i in range(3):
        make_event(
            db_session,
            test_event_type.id,
            name=f"Event {i}",
            start_offset_hours=3 + i,
            end_offset_hours=4 + i,
        )

    response = client.get("/events/activeEvents")

    assert response.status_code == 200
    response_data: dict[str, Any] = cast(dict[str, Any], response.json())
    events: list[Any] = cast(list[Any], response_data["events"])
    assert len(events) == 3


def test_get_active_events_returns_500_on_unexpected_error(
    app: FastAPI,
    client: TestClient,
) -> None:
    """Test GET returns 500 on unexpected error."""

    def broken_service():
        raise Exception("something went wrong")

    mock_serv = EventRegisterService.__new__(EventRegisterService)
    mock_serv.get_active_events = broken_service

    app.dependency_overrides[get_event_reg_serv] = lambda: mock_serv

    response = client.get("/events/activeEvents")

    app.dependency_overrides.clear()

    assert response.status_code == 500
    response_data: dict[str, Any] = cast(dict[str, Any], response.json())
    detail: Any = response_data.get("detail")
    assert detail == "An internal server error occurred"


def test_get_events_returns_events_without_event_name(
    app: FastAPI,
    client: TestClient,
) -> None:
    """GET /events/events should allow callers to omit the optional event_name filter."""
    start = datetime.now(UTC) + timedelta(hours=1)
    end = start + timedelta(hours=1)
    event = Event(
        id="event-1",
        name="Open House",
        description="Meet the team",
        start_datetime=start,
        end_datetime=end,
        location="Room A",
        type_id=1,
    )
    mock_serv = Mock(spec=EventRegisterService)
    mock_serv.get_events.return_value = [event]
    app.dependency_overrides[get_event_reg_serv] = lambda: mock_serv

    response = client.get("/events/events?page=1")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    mock_serv.get_events.assert_called_once_with(1, None)
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert data["events"] == [
        {
            "id": "event-1",
            "name": "Open House",
            "description": "Meet the team",
            "start_datetime": start.isoformat().replace("+00:00", "Z"),
            "end_datetime": end.isoformat().replace("+00:00", "Z"),
            "location": "Room A",
            "type_id": 1,
        }
    ]


def test_get_events_passes_event_name_filter(
    app: FastAPI,
    client: TestClient,
) -> None:
    """GET /events/events should pass the optional filter through to the service."""
    mock_serv = Mock(spec=EventRegisterService)
    mock_serv.get_events.return_value = []
    app.dependency_overrides[get_event_reg_serv] = lambda: mock_serv

    response = client.get("/events/events?page=2&event_name=workshop")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {"events": []}
    mock_serv.get_events.assert_called_once_with(2, "workshop")


def test_post_events_success(client: TestClient) -> None:
    """Test creating event via POST /events endpoint."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Team Meeting",
            "description": "Weekly sync",
            "location": "Room A",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert "id" in data
    assert data["status"] == "created"
    assert len(data["id"]) == 36  # UUID length


def test_post_events_returns_correct_response_schema(client: TestClient) -> None:
    """Test that response matches EventCreatedResponse schema."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Test Event",
            "description": "Test",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201
    data: dict[str, Any] = cast(dict[str, Any], response.json())

    # Verify exact schema
    assert set(data.keys()) == {"id", "status"}
    assert isinstance(data["id"], str)
    assert isinstance(data["status"], str)
    assert data["status"] == "created"


def test_post_events_with_all_fields(client: TestClient) -> None:
    """Test POST with all fields populated."""
    start = (datetime.now(UTC) + timedelta(hours=5)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=6)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Complete Event",
            "description": "All fields populated",
            "location": "Conference Room B",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert data["status"] == "created"


# ============================================================================
# TEST: POST /events - Validation Errors
# ============================================================================


def test_post_events_start_datetime_in_past(client: TestClient) -> None:
    """Test that POST rejects past start_datetime."""
    start = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Past Event",
            "description": "In the past",
            "location": "Room A",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 400
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert "start_datetime cannot be in the past" in data["detail"]


def test_post_events_end_before_start(client: TestClient) -> None:
    """Test that POST rejects end_datetime before start_datetime."""
    start = (datetime.now(UTC) + timedelta(hours=2)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Invalid Event",
            "description": "End before start",
            "location": "Room A",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 400
    response_data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert "end_datetime must be after start_datetime" in response_data["detail"]


def test_post_events_missing_required_field(client: TestClient) -> None:
    """Test that POST rejects missing required fields."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    # Missing 'name' field
    response = client.post(
        "/events",
        json={
            "description": "Missing name",
            "location": "Room A",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 422  # Validation error


def test_post_events_invalid_datetime_format(client: TestClient) -> None:
    """Test that POST rejects invalid datetime format."""
    response = client.post(
        "/events",
        json={
            "name": "Bad DateTime Event",
            "description": "Invalid format",
            "location": "Room A",
            "type_id": 1,
            "start_datetime": "invalid-datetime",
            "end_datetime": "also-invalid",
        },
    )

    assert response.status_code == 422


def test_post_events_null_fields(client: TestClient) -> None:
    """Test that POST rejects null required fields."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": None,  # Null name
            "description": "Test",
            "location": "Room A",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 422


# ============================================================================
# TEST: POST /events - Content Type & Format
# ============================================================================


def test_post_events_with_json_content_type(client: TestClient) -> None:
    """Test POST with correct Content-Type."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Event",
            "description": "Test",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 201


def test_post_events_empty_body(client: TestClient) -> None:
    """Test that POST with empty body is rejected."""
    response = client.post("/events", json={})
    assert response.status_code == 422


def test_post_events_extra_fields_ignored(client: TestClient) -> None:
    """Test that extra fields in request are ignored."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Event",
            "description": "Test",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
            "extra_field": "should_be_ignored",
            "another_extra": 12345,
        },
    )

    assert response.status_code == 201


# ============================================================================
# TEST: POST /events - Multiple Requests
# ============================================================================


def test_post_events_multiple_times(client: TestClient) -> None:
    """Test creating multiple events in sequence."""
    event_ids: list[str] = []

    for i in range(3):
        start = (datetime.now(UTC) + timedelta(hours=i + 1)).isoformat()
        end = (datetime.now(UTC) + timedelta(hours=i + 2)).isoformat()

        response = client.post(
            "/events",
            json={
                "name": f"Event {i}",
                "description": f"Test {i}",
                "location": f"Room {i}",
                "type_id": 1,
                "start_datetime": start,
                "end_datetime": end,
            },
        )

        assert response.status_code == 201
        response_data: dict[str, Any] = cast(dict[str, Any], response.json())
        event_id: str = cast(str, response_data["id"])
        event_ids.append(event_id)

    # Verify all are unique
    result: set[str] = set(event_ids)
    assert len(result) == 3


def test_post_events_concurrent_creation(client: TestClient) -> None:
    """Test creating multiple events with different data."""
    base_time = datetime.now(UTC)

    responses: list[Any] = []
    for i in range(5):
        start = (base_time + timedelta(hours=i + 1)).isoformat()
        end = (base_time + timedelta(hours=i + 2)).isoformat()

        response = client.post(
            "/events",
            json={
                "name": f"Event {i}",
                "description": f"Description {i}",
                "location": f"Location {i}",
                "type_id": 1,
                "start_datetime": start,
                "end_datetime": end,
            },
        )
        responses.append(response)

    # All should succeed
    assert all(r.status_code == 201 for r in responses)
    # All should have different IDs
    ids: list[str] = [cast(str, r.json()["id"]) for r in responses]
    assert len(set(ids)) == 5


# ============================================================================
# TEST: POST /events - Edge Cases
# ============================================================================


def test_post_events_with_very_long_name(client: TestClient) -> None:
    """Test POST with very long event name."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    long_name = "A" * 500

    response = client.post(
        "/events",
        json={
            "name": long_name,
            "description": "Test",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201


def test_post_events_with_special_characters(client: TestClient) -> None:
    """Test POST with special characters in fields."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Event @ #1 (2026) - Special!",
            "description": "Description with 'quotes' and \"double quotes\"",
            "location": "Room A/B, Building #1",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201


def test_post_events_with_unicode_characters(client: TestClient) -> None:
    """Test POST with unicode characters."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Event 🎉 日本語 Français",
            "description": "Unicode test",
            "location": "Room 北京",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201


def test_post_events_with_minimal_duration(client: TestClient) -> None:
    """Test POST with 1 second event duration."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=1, seconds=1)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Short Event",
            "description": "1 second",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201


# ============================================================================
# TEST: HTTP Status Codes
# ============================================================================


def test_post_events_returns_201_status_code(client: TestClient) -> None:
    """Test that successful POST returns 201 Created."""
    start = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=2)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Event",
            "description": "Test",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 201


def test_post_events_returns_400_for_validation_error(client: TestClient) -> None:
    """Test that validation error returns 400 Bad Request."""
    start = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    end = (datetime.now(UTC) + timedelta(hours=1)).isoformat()

    response = client.post(
        "/events",
        json={
            "name": "Event",
            "description": "Test",
            "location": "Room",
            "type_id": 1,
            "start_datetime": start,
            "end_datetime": end,
        },
    )

    assert response.status_code == 400


# ============================================================================
# TEST: PUT /events/{event_id}
# ============================================================================


def test_put_event_updates_name(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    event = make_event(db_session, test_event_type.id, name="Original Name")

    response = client.put(
        f"/events/{event.id}",
        json={"name": "Updated Name"},
    )

    assert response.status_code == 200
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert data["name"] == "Updated Name"
    assert data["id"] == str(event.id)


def test_put_event_updates_location(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    event = make_event(db_session, test_event_type.id, name="Event")

    response = client.put(
        f"/events/{event.id}",
        json={"location": "New Location"},
    )

    assert response.status_code == 200
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert data["location"] == "New Location"


def test_put_event_updates_multiple_fields(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    event = make_event(db_session, test_event_type.id, name="Old Name")
    new_start = (datetime.now(UTC) + timedelta(hours=3)).isoformat()
    new_end = (datetime.now(UTC) + timedelta(hours=4)).isoformat()

    response = client.put(
        f"/events/{event.id}",
        json={
            "name": "New Name",
            "location": "New Location",
            "start_datetime": new_start,
            "end_datetime": new_end,
        },
    )

    assert response.status_code == 200
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert data["name"] == "New Name"
    assert data["location"] == "New Location"


def test_put_event_no_fields_returns_400(
    client: TestClient,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test PUT returns 400 when no fields are provided."""
    event = make_event(db_session, test_event_type.id, name="Event")

    response = client.put(
        f"/events/{event.id}",
        json={},
    )

    assert response.status_code == 400
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert "no fields provided" in data["detail"].lower()


def test_put_event_not_found_returns_404(
    client: TestClient,
    db_session: Session,
) -> None:
    """Test PUT returns 404 for non-existent event id."""
    fake_id = "00000000-0000-0000-0000-000000000000"

    response = client.put(
        f"/events/{fake_id}",
        json={"name": "Doesn't Matter"},
    )

    assert response.status_code == 404
    data: dict[str, Any] = cast(dict[str, Any], response.json())
    assert "not found" in data["detail"].lower()


# ============================================================================
# TEST: GET /events/eventTypes
# ============================================================================


def test_get_event_types_returns_200_with_event_types(
    client: TestClient,
    test_event_type: EventType,
) -> None:
    """Test GET /events/eventTypes returns event types."""
    response = client.get("/events/eventTypes")

    assert response.status_code == 200
    data = response.json()
    assert "event_types" in data
    event_types = cast(list[dict[str, object]], data["event_types"])
    assert len(event_types) == 1
    assert event_types[0]["key"] == "Workshop"
    assert event_types[0]["id"] == test_event_type.id


def test_get_event_types_returns_200_with_empty_list(
    client: TestClient,
    db_session: Session,
) -> None:
    """Test GET /events/eventTypes returns empty list when no event types exist."""
    db_session.query(EventType).delete()
    db_session.commit()

    response = client.get("/events/eventTypes")

    assert response.status_code == 200
    assert response.json() == {"event_types": []}


def test_get_event_types_returns_500_on_unexpected_error(
    app: FastAPI,
    client: TestClient,
) -> None:
    """Test GET /events/eventTypes returns 500 on unexpected error."""

    def broken_service():
        raise Exception("something went wrong")

    mock_serv = EventRegisterService.__new__(EventRegisterService)
    mock_serv.get_event_types = broken_service

    app.dependency_overrides[get_event_reg_serv] = lambda: mock_serv

    response = client.get("/events/eventTypes")

    app.dependency_overrides.clear()

    assert response.status_code == 500
    data = response.json()
    assert data.get("detail") == "An internal server error occurred"
