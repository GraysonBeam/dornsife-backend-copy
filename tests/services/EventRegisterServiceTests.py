import logging
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from logging import Logger

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.Models.Base import Base
from src.Models.Event import Event
from src.Models.EventType import EventType
from src.Repositories.EventsRepository import EventsRepository
from src.Schemas.GetActiveEventsResponse import ActiveEvent
from src.Services.EventRegisterService import EventRegisterService


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def logger() -> Logger:
    return logging.getLogger("test_event_register_service_logger")


@pytest.fixture
def events_repo(logger: Logger, db_session: Session) -> EventsRepository:
    return EventsRepository(logger, db_session)


@pytest.fixture
def service(logger: Logger, events_repo: EventsRepository) -> EventRegisterService:
    return EventRegisterService(logger, events_repo)


@pytest.fixture
def test_event_type(db_session: Session) -> EventType:
    event_type = EventType(type="Workshop")
    db_session.add(event_type)
    db_session.commit()
    return event_type


def make_event(
    db_session: Session,
    event_type_id: int,
    *,
    name: str = "Event",
    start_offset_hours: float = 1,
    end_offset_hours: float = 2,
) -> Event:
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


def test_get_active_events_returns_empty_when_no_events(
    service: EventRegisterService,
) -> None:
    result = service.get_active_events()

    assert result == []


def test_get_active_events_returns_list_of_active_events(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    make_event(
        db_session, test_event_type.id, name="Soon", start_offset_hours=6, end_offset_hours=7
    )

    result = service.get_active_events()

    assert len(result) == 1
    assert isinstance(result[0], ActiveEvent)


def test_get_active_events_contains_correct_types(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    make_event(
        db_session, test_event_type.id, name="Soon", start_offset_hours=6, end_offset_hours=7
    )

    result = service.get_active_events()

    event = result[0]
    assert isinstance(event.id, str)
    assert isinstance(event.name, str)
    assert isinstance(event.start_datetime, datetime)
    assert isinstance(event.end_datetime, datetime)


def test_get_active_events_contains_correct_values(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    db_event = make_event(
        db_session, test_event_type.id, name="My Event", start_offset_hours=6, end_offset_hours=7
    )

    result = service.get_active_events()

    event = result[0]
    assert event.id == str(db_event.id)
    assert event.name == "My Event"
    assert event.start_datetime == db_event.start_datetime
    assert event.end_datetime == db_event.end_datetime


def test_get_active_events_returns_multiple_events(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    for i in range(3):
        make_event(
            db_session,
            test_event_type.id,
            name=f"Event {i}",
            start_offset_hours=3 + i,
            end_offset_hours=4 + i,
        )

    result = service.get_active_events()

    assert len(result) == 3


def test_get_active_events_excludes_inactive_events(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Events outside both time windows should not appear in the result."""
    make_event(
        db_session, test_event_type.id, name="Active", start_offset_hours=6, end_offset_hours=7
    )
    make_event(
        db_session, test_event_type.id, name="Too Old", start_offset_hours=-12, end_offset_hours=-9
    )
    make_event(
        db_session, test_event_type.id, name="Too Far", start_offset_hours=24, end_offset_hours=25
    )

    result = service.get_active_events()

    names = [r.name for r in result]
    assert "Active" in names
    assert "Too Old" not in names
    assert "Too Far" not in names


def test_validate_event_id_passes_real_id(
    service: EventRegisterService, db_session: Session, test_event_type: EventType
) -> None:
    db_event = make_event(
        db_session, test_event_type.id, name="My Event", start_offset_hours=6, end_offset_hours=7
    )

    result = service.validate_event_id(db_event.id)

    assert result


def test_validate_event_id_flags_nonexistent_id(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    result = service.validate_event_id("1")

    assert not result


def test_create_event_success(
    service: EventRegisterService,
    db_session: Session,
    test_event_type: EventType,
) -> None:
    """Test create_event successfully creates and persists event."""
    from src.Schemas.EventCreatedResponse import EventCreatedResponse
    from src.Schemas.EventRegistrationRequest import EventRegistrationRequest

    start = datetime.now(UTC) + timedelta(hours=1)  # ✅ Use UTC
    end = datetime.now(UTC) + timedelta(hours=2)

    request = EventRegistrationRequest(
        name="Team Meeting",
        description="Weekly sync",
        location="Room A",
        type_id=test_event_type.id,
        start_datetime=start,
        end_datetime=end,
    )

    response = service.create_event(request)

    assert isinstance(response, EventCreatedResponse)
    assert response.status == "created"

    saved = db_session.query(Event).filter(Event.id == response.id).first()
    assert saved is not None
    assert saved.name == "Team Meeting"


def test_create_event_validates_time_range(
    service: EventRegisterService,
    test_event_type: EventType,
) -> None:
    """Test create_event validates start/end times."""
    from src.Schemas.EventRegistrationRequest import EventRegistrationRequest
    from src.Utils.Validators import ValidationError

    start = datetime.now(UTC) - timedelta(hours=1)
    end = datetime.now(UTC) + timedelta(hours=1)

    request = EventRegistrationRequest(
        name="Event",
        description="Test",
        location="Room",
        type_id=test_event_type.id,
        start_datetime=start,
        end_datetime=end,
    )

    with pytest.raises(ValidationError):
        service.create_event(request)


def test_get_event_types_success(
    service: EventRegisterService,
    test_event_type: EventType,
) -> None:
    from src.Schemas.EventTypesResponse import EventTypeItem

    res = service.get_event_types()
    assert res is not None
    assert len(res) == 1
    assert isinstance(res[0], EventTypeItem)
    assert res[0].key == "Workshop"
    assert res[0].id == test_event_type.id


def test_get_event_types_empty(
    service: EventRegisterService,
    db_session: Session,
) -> None:
    db_session.query(EventType).delete()
    db_session.commit()

    res = service.get_event_types()
    assert res is None
